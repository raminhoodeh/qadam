const STATUS_SOURCES = [
    {
        key: "live_bridge",
        label: "read-only live status",
        url: "/api/cockpit-status",
        requiresAuth: true
    },
    {
        key: "static_snapshot",
        label: "static snapshot fallback",
        url: "/status/cockpit-status.json",
        requiresAuth: false
    }
];

const DASHBOARD_VIEWS = [
    { id: "overview", label: "Overview" },
    { id: "trades", label: "Trades" },
    { id: "evidence", label: "Evidence" },
    { id: "reasoning", label: "Reasoning" },
    { id: "operations", label: "Operations" }
];
const DASHBOARD_VIEW_IDS = new Set(DASHBOARD_VIEWS.map((view) => view.id));
const DASHBOARD_STATUS_REFRESH_MS = 60000;
let dashboardStatusRefreshTimer = null;
const DASHBOARD_ADVANCED_DEBUG_KEY = "qadam.dashboard.advanced_debug";
const DASHBOARD_LEGACY_HASH_TARGETS = {
    sources: { viewId: "evidence", targetId: "watching" },
    performance: { viewId: "trades", targetId: "money" },
    "mission-control": { viewId: "overview", targetId: "mission-control" },
    "review-sequence": { viewId: "overview", targetId: "review-sequence" },
    watching: { viewId: "evidence", targetId: "watching" },
    cognition: { viewId: "reasoning", targetId: "cognition" },
    "strategy-manifestation": { viewId: "reasoning", targetId: "strategy-manifestation" },
    worldview: { viewId: "reasoning", targetId: "worldview" },
    "trade-layer": { viewId: "trades", targetId: "trade-layer" },
    money: { viewId: "trades", targetId: "money" },
    "system-map": { viewId: "operations", targetId: "system-map" },
    forbidden: { viewId: "operations", targetId: "operations-readout" },
    "process-console": { viewId: "operations", targetId: "operations-readout" },
    communications: { viewId: "operations", targetId: "operations-readout" },
    governance: { viewId: "operations", targetId: "operations-readout" }
};
const DASHBOARD_VIEW_SCROLL_KEY = "qadam.dashboard.view.scroll";
const TRADE_WORKSPACE_FILTERS = [
    { id: "all", label: "All" },
    { id: "active", label: "Active" },
    { id: "blocked", label: "Safety stops" },
    { id: "open", label: "Open" },
    { id: "closed", label: "Closed" },
    { id: "postmortem_due", label: "Postmortem due" }
];
const OPERATIONS_ROLE_SPINE = [
    {
        key: "fund_manager",
        label: "Fund Manager supervisor",
        role: "One overseeing Fund Manager",
        node_keys: ["fund_manager_forum", "signal_review"],
        summary: "Human review, challenge, governance comments, kill-switch review, and phase promotion decisions.",
        authority: "Supervisor only; not a manual trade-execution node.",
        href: "#operations"
    },
    {
        key: "live_data_feeds",
        label: "Live data feed clusters",
        role: "Intelligence pipelines",
        node_keys: ["watching", "yahoo_finance", "preference_mcp"],
        summary: "Canonical and supplemental world, market, broker, prediction-market, filings, and narrative inputs.",
        authority: "Observation only; no source can create orders.",
        href: "#evidence"
    },
    {
        key: "coo",
        label: "Qadam Orchestrator",
        role: "Local coordinator",
        node_keys: ["event_log", "live_bridge"],
        summary: "Records system events, exports sanitized state, and keeps the dashboard read-only.",
        authority: "Exporter only; no browser shell or broker route.",
        href: "#operations"
    },
    {
        key: "research_analyst",
        label: "Local LLM Research Analyst",
        role: "Local research desk",
        node_keys: ["research_analyst", "shadow_intelligence"],
        summary: "Compresses noisy observations into research packets.",
        authority: "No execution authority.",
        href: "#reasoning"
    },
    {
        key: "strategy_lead",
        label: "Frontier LLM Strategy Lead",
        role: "Strategy challenge desk",
        node_keys: ["strategy_lead", "worldview"],
        summary: "Challenges hypotheses and strategy families after evidence exists.",
        authority: "Challenge-only; cannot stage or approve orders.",
        href: "#reasoning"
    },
    {
        key: "head_of_quant",
        label: "Quantum/Classical Head of Quant",
        role: "Bounded quant oracle",
        node_keys: ["head_of_quant"],
        summary: "Runs bounded quant checks and exposes classical fallback or hardware-readiness state.",
        authority: "Non-executable oracle; cannot originate trades.",
        href: "#operations"
    },
    {
        key: "signal_risk_gates",
        label: "Signal/Risk Gates",
        role: "Safety and sizing gates",
        node_keys: ["signal_integrity_gate", "approval_policy_router", "risk_agent", "kill_switch_ledger", "execution_policy", "execution_adapter_status", "staged_order_contract", "broker_reconciliation", "paper_submit_receipt", "prediction_market_adapter"],
        summary: "Blocks stale, weak, oversized, unauthorized, or write-capable paths before paper state.",
        authority: "Blocked unless safe.",
        href: "#trades"
    },
    {
        key: "paper_lifecycle",
        label: "Paper Lifecycle",
        role: "Paper execution mirror",
        node_keys: ["trade_layer", "paper_account", "position_monitor"],
        summary: "Tracks observed signals, trade ideas, paper orders, positions, exits, and receipts.",
        authority: "Paper/demo state only; live capital disabled.",
        href: "#trades"
    },
    {
        key: "learning_loop",
        label: "Learning Loop",
        role: "Postmortem and memory",
        node_keys: ["postmortem_loop"],
        summary: "Returns closed paper outcomes, postmortems, and approved learning proposals to Qadam memory.",
        authority: "After-action review only.",
        href: "#trades"
    }
];
const OPERATIONS_PIPELINE_LABELS = {
    conflict: "Conflict and geopolitics",
    physical: "Physical world, energy, shipping, and weather",
    macro: "Macro, rates, and policy",
    market: "Markets, broker, and prediction markets",
    social: "Narrative, filings, social, and news"
};
const DASHBOARD_CORE_SOURCE_KEYS = new Set([
    "acled",
    "gdelt",
    "oref",
    "nasa_firms",
    "fred",
    "polymarket",
    "alpaca",
    "rss",
    "telegram",
    "tradingview_paid_alerts"
]);
const CANONICAL_STATUS_LANGUAGE = {
    current: {
        label: "OK",
        tone: "online",
        description: "Verified enough to treat as a healthy dashboard state.",
        tokens: ["online", "ok", "ready", "connected", "available", "active", "configured", "validated", "certified", "approved", "passed", "complete", "written", "full paper operational ready", "submitted to alpaca paper"]
    },
    "read-only": {
        label: "OK - read-only",
        tone: "online",
        description: "Visible for monitoring only. It cannot mutate Qadam state.",
        tokens: ["read-only", "read only", "read_only", "read-only ready", "read_only_ready"]
    },
    "paper-only": {
        label: "OK - paper only",
        tone: "online",
        description: "Paper/demo state only. Live capital remains off.",
        tokens: ["paper only", "paper/demo only", "paper mode", "paper"]
    },
    "live-capital-off": {
        label: "OK - live capital off",
        tone: "online",
        description: "Real-money trading authority is off.",
        tokens: ["live capital disabled", "live capital off"]
    },
    "dry-run": {
        label: "Dry run",
        tone: "pending",
        description: "Prepared for simulation or notification testing without live send/write authority.",
        tokens: ["dry run", "dry-run", "dry_run", "queued dry run", "dry-run planned"]
    },
    optional: {
        label: "Optional",
        tone: "pending",
        description: "Useful if configured, but not required for the current paper-trading core.",
        tokens: ["optional", "not required", "supplemental only", "ready to build", "fallback only", "receiver pending", "live read deferred", "disabled live mode", "live mcp disabled"]
    },
    "waiting-for-evidence": {
        label: "Waiting",
        tone: "pending",
        description: "Normal hold state while Qadam waits for source, model, risk, or review evidence.",
        tokens: ["pending", "waiting", "not ready", "not_ready", "not run", "not-run", "not requested", "not_requested", "deferred", "planned"]
    },
    "missing-setup": {
        label: "Not configured",
        tone: "degraded",
        description: "Required configuration, credentials, source material, or exported status is missing.",
        tokens: ["missing", "not configured", "not exported", "missing credential", "credential missing", "status unavailable", "not connected", "unavailable"]
    },
    degraded: {
        label: "Needs attention",
        tone: "degraded",
        description: "Available but impaired, stale, partial, or lower confidence.",
        tokens: ["degraded", "needs attention", "stale", "fallback", "partial", "weak"]
    },
    "local-only": {
        label: "Local only",
        tone: "local-only",
        description: "Present only in local/private runtime context.",
        tokens: ["local only", "local-only", "local_only"]
    },
    "non-executable": {
        label: "Review only",
        tone: "blocked",
        description: "Can inform review, but cannot create or execute a trade action.",
        tokens: ["non executable", "non-executable", "non_executable", "research only", "research-only", "context only", "prior only", "challenge only", "challenge-only"]
    },
    "safety-stop": {
        label: "Blocked",
        tone: "blocked",
        description: "A deliberate safety, authority, risk, or policy stop is holding the path.",
        tokens: ["blocked", "blocked before", "blocked_by_policy", "disabled contract hold", "disabled_contract_hold", "hard block", "kill switch", "no-submit", "live blocked"]
    },
    fault: {
        label: "Fault",
        tone: "blocked",
        description: "An unexpected failure or unsafe condition needs operator review.",
        tokens: ["failed", "failure", "error", "fault", "unsafe", "write enabled", "live capital enabled", "display inferred", "ui inferred"]
    }
};
const CANONICAL_STATUS_BY_TOKEN = Object.fromEntries(
    Object.entries(CANONICAL_STATUS_LANGUAGE).flatMap(([key, record]) => (
        record.tokens.map((token) => [String(token).toLowerCase().replaceAll("_", " ").replaceAll("-", " ").trim(), { key, ...record }])
    ))
);

function dashboardQuery(selector) {
    return document.querySelector(selector);
}

function readDashboardViewScrollState() {
    try {
        if (typeof sessionStorage === "undefined") return {};
        return JSON.parse(sessionStorage.getItem(DASHBOARD_VIEW_SCROLL_KEY) || "{}");
    } catch (_error) {
        return {};
    }
}

function writeDashboardViewScrollState(state) {
    try {
        if (typeof sessionStorage !== "undefined") {
            sessionStorage.setItem(DASHBOARD_VIEW_SCROLL_KEY, JSON.stringify(state));
        }
    } catch (_error) {
        // Scroll restoration is a convenience; view switching should still work.
    }
}

function dashboardViewLabel(viewId) {
    return DASHBOARD_VIEWS.find((view) => view.id === viewId)?.label || "Overview";
}

function currentDashboardView() {
    return document.documentElement?.dataset.dashboardActiveView || "overview";
}

function readDashboardDebugPreference() {
    if (typeof window === "undefined" || !window.localStorage) return false;
    try {
        return window.localStorage.getItem(DASHBOARD_ADVANCED_DEBUG_KEY) === "on";
    } catch (_error) {
        return false;
    }
}

function writeDashboardDebugPreference(enabled) {
    if (typeof window === "undefined" || !window.localStorage) return;
    try {
        window.localStorage.setItem(DASHBOARD_ADVANCED_DEBUG_KEY, enabled ? "on" : "off");
    } catch (_error) {
        // Preference storage is optional; the in-page mode still updates.
    }
}

function dashboardDebugModeEnabled() {
    return document.documentElement?.dataset.dashboardDebug === "on";
}

function resolveDashboardHash(hash = "") {
    const target = String(hash || "").replace(/^#/, "");
    if (!target) return { viewId: "overview", targetId: "mission-control", legacy: false };
    if (DASHBOARD_VIEW_IDS.has(target)) return { viewId: target, targetId: null, legacy: false };
    if (DASHBOARD_LEGACY_HASH_TARGETS[target]) {
        return { ...DASHBOARD_LEGACY_HASH_TARGETS[target], legacy: true };
    }
    return { viewId: "overview", targetId: "mission-control", legacy: false };
}

function setDashboardViewSectionVisibility(viewId) {
    if (typeof document.querySelectorAll !== "function") return;
    const debugEnabled = dashboardDebugModeEnabled();
    document.querySelectorAll("[data-dashboard-view-section]").forEach((section) => {
        const debugOnly = section.hasAttribute("data-dashboard-debug-only");
        const active = section.dataset.dashboardViewSection === viewId && (!debugOnly || debugEnabled);
        section.hidden = !active;
        section.setAttribute("aria-hidden", active ? "false" : "true");
    });
    document.querySelectorAll("[data-dashboard-debug-only]:not([data-dashboard-view-section])").forEach((section) => {
        section.hidden = !debugEnabled;
        section.setAttribute("aria-hidden", debugEnabled ? "false" : "true");
    });
}

function setDashboardViewNavigationState(viewId) {
    if (typeof document.querySelectorAll !== "function") return;
    const current = dashboardQuery("[data-dashboard-view-current]") || dashboardQuery("[data-cockpit-nav-current]");
    document.querySelectorAll("[data-dashboard-view-link]").forEach((link) => {
        const active = link.dataset.dashboardViewTarget === viewId;
        link.classList.toggle("active", active);
        if (active) {
            link.setAttribute("aria-current", "page");
            if (current) current.textContent = link.textContent || dashboardViewLabel(viewId);
        } else {
            link.removeAttribute("aria-current");
        }
    });
}

function setDashboardDebugControls(enabled) {
    if (typeof document.querySelectorAll !== "function") return;
    document.querySelectorAll("[data-dashboard-debug-toggle]").forEach((button) => {
        button.setAttribute("aria-pressed", enabled ? "true" : "false");
        button.setAttribute("aria-expanded", enabled ? "true" : "false");
        button.classList.toggle("active", enabled);
        button.textContent = enabled ? "Hide diagnostics" : "Diagnostics";
    });
    document.querySelectorAll("[data-dashboard-advanced-links]").forEach((links) => {
        links.hidden = !enabled;
        links.setAttribute("aria-hidden", enabled ? "false" : "true");
    });
}

function setDashboardDebugMode(enabled, options = {}) {
    const nextEnabled = Boolean(enabled);
    if (document.documentElement) {
        document.documentElement.dataset.dashboardDebug = nextEnabled ? "on" : "off";
    }
    setDashboardDebugControls(nextEnabled);
    if (options.persist !== false) writeDashboardDebugPreference(nextEnabled);
    setDashboardViewSectionVisibility(currentDashboardView());
}

function storeDashboardViewScrollPosition(viewId) {
    if (typeof window === "undefined") return;
    const state = readDashboardViewScrollState();
    state[viewId] = Math.max(0, Math.round(Number(window.scrollY || 0)));
    writeDashboardViewScrollState(state);
}

function dashboardStickyScrollOffset() {
    if (typeof document === "undefined") return 0;
    const stickySelectors = [".cockpit-nav", "[data-dashboard-safety-strip]"];
    const measuredOffset = stickySelectors.reduce((offset, selector) => {
        const node = document.querySelector?.(selector);
        if (!node || typeof node.getBoundingClientRect !== "function") return offset;
        const styles = typeof window !== "undefined" && window.getComputedStyle
            ? window.getComputedStyle(node)
            : null;
        if (styles && styles.display === "none") return offset;
        const rect = node.getBoundingClientRect();
        return Math.max(offset, rect.bottom || 0);
    }, 0) + 12;
    const estimatedStickyStack = typeof window !== "undefined" && window.innerWidth < 700 ? 260 : 220;
    return Math.max(measuredOffset, estimatedStickyStack);
}

function scrollDashboardTargetIntoView(target) {
    if (!target || typeof window === "undefined") return false;
    if (typeof target.getBoundingClientRect === "function" && typeof window.scrollTo === "function") {
        const top = Math.max(0, (window.scrollY || 0) + target.getBoundingClientRect().top - dashboardStickyScrollOffset());
        window.scrollTo({ top, behavior: "auto" });
        return true;
    }
    if (target.scrollIntoView) {
        target.scrollIntoView({ block: "start" });
        return true;
    }
    return false;
}

function restoreDashboardViewScrollPosition(viewId, targetId, shouldScroll) {
    if (!shouldScroll || typeof window === "undefined") return;
    const restore = () => {
        const target = targetId && typeof document.getElementById === "function"
            ? document.getElementById(targetId)
            : null;
        if (scrollDashboardTargetIntoView(target)) {
            return;
        }
        const state = readDashboardViewScrollState();
        if (typeof window.scrollTo === "function") {
            window.scrollTo({ top: state[viewId] || 0, behavior: "auto" });
        }
    };
    if (typeof window.requestAnimationFrame === "function") {
        window.requestAnimationFrame(restore);
    } else {
        restore();
    }
}

function activateDashboardView(viewId, options = {}) {
    const resolved = DASHBOARD_VIEW_IDS.has(viewId) ? viewId : "overview";
    if (resolved !== "overview" && !dashboardDebugModeEnabled()) {
        setDashboardDebugMode(true, { persist: options.persistDebug !== false, scroll: false });
    }
    const previous = currentDashboardView();
    if (previous !== resolved) storeDashboardViewScrollPosition(previous);
    if (document.documentElement) {
        document.documentElement.dataset.dashboardActiveView = resolved;
    }
    setDashboardViewSectionVisibility(resolved);
    setDashboardViewNavigationState(resolved);
    restoreDashboardViewScrollPosition(resolved, options.targetId, options.scroll !== false);
    return resolved;
}

function activateDashboardViewFromHash(hash, options = {}) {
    const resolved = resolveDashboardHash(hash);
    return activateDashboardView(resolved.viewId, {
        targetId: resolved.targetId,
        scroll: options.scroll
    });
}

function initCockpitNavigation() {
    if (typeof document.querySelectorAll !== "function") return;
    const links = Array.from(document.querySelectorAll("[data-dashboard-view-link]"));
    if (!links.length) return;
    const initialHash = typeof window !== "undefined" ? window.location?.hash || "" : "";
    const initialResolved = resolveDashboardHash(initialHash);
    setDashboardDebugMode(readDashboardDebugPreference() || initialResolved.viewId !== "overview", {
        persist: false,
        scroll: false
    });

    links.forEach((link) => {
        link.addEventListener("click", (event) => {
            const viewId = link.dataset.dashboardViewTarget || "overview";
            if (!DASHBOARD_VIEW_IDS.has(viewId)) return;
            event?.preventDefault?.();
            if (typeof window !== "undefined" && window.history?.pushState) {
                window.history.pushState(null, "", `#${viewId}`);
            }
            activateDashboardView(viewId);
        });
    });

    document.querySelectorAll("[data-dashboard-debug-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            setDashboardDebugMode(!dashboardDebugModeEnabled(), { persist: true, scroll: true });
        });
    });

    activateDashboardViewFromHash(initialHash, { scroll: false });

    if (typeof window !== "undefined" && window.addEventListener) {
        window.addEventListener("hashchange", () => {
            activateDashboardViewFromHash(window.location?.hash || "", { scroll: true });
        });
        window.addEventListener("popstate", () => {
            activateDashboardViewFromHash(window.location?.hash || "", { scroll: true });
        });
    }
}

function dashboardText(value, fallback = "Not connected yet") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value)
        .replace(/\bPhase\s*7\b/gi, "60-day paper growth trial")
        .replace(/\bQ7-15\b/g, "Paper Growth Trial")
        .replace(/\bQ7-16\b/g, "Growth Review")
        .replace(/\bQ7\b/g, "Paper Growth Trial")
        .replace(/phase7[_ -]?demo[_ -]?proof/gi, "paper growth trial")
        .replace(/phase7[_ -]?proof/gi, "paper growth proof")
        .replace(/\bphase7\b/gi, "paper growth")
        .replace(/30[- ]day demo[- ]proof/gi, "60-day paper growth")
        .replace(/30 consecutive calendar day/gi, "60-day paper growth")
        .replace(/100[- ]trade maturity/gi, "2x portfolio target")
        .replaceAll("_", " ");
}

function normalizeCanonicalStatusToken(value) {
    return String(value || "")
        .replaceAll("_", " ")
        .replaceAll("-", " ")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
}

function canonicalStatusRecord(value, options = {}) {
    const token = normalizeCanonicalStatusToken(dashboardText(value, options.fallback || "not exported"));
    const exact = CANONICAL_STATUS_BY_TOKEN[token];
    if (exact) return exact;
    if (options.strict) return null;
    if (/ui inferred|display inferred|unsafe|failed|failure|error|fault|write enabled|live capital enabled/.test(token)) return { key: "fault", ...CANONICAL_STATUS_LANGUAGE.fault };
    if (/blocked|hard block|kill switch|no submit|disabled contract|live blocked/.test(token)) return { key: "safety-stop", ...CANONICAL_STATUS_LANGUAGE["safety-stop"] };
    if (/missing|not exported|not connected|credential|unavailable/.test(token)) return { key: "missing-setup", ...CANONICAL_STATUS_LANGUAGE["missing-setup"] };
    if (/degraded|stale|fallback|partial|weak/.test(token)) return { key: "degraded", ...CANONICAL_STATUS_LANGUAGE.degraded };
    if (/optional|not required|supplemental only|ready to build|fallback only|receiver pending|disabled live mode|live mcp disabled/.test(token)) return { key: "optional", ...CANONICAL_STATUS_LANGUAGE.optional };
    if (/pending|waiting|deferred|not ready|not run|planned/.test(token)) return { key: "waiting-for-evidence", ...CANONICAL_STATUS_LANGUAGE["waiting-for-evidence"] };
    if (/dry run|queued/.test(token)) return { key: "dry-run", ...CANONICAL_STATUS_LANGUAGE["dry-run"] };
    if (/read only|public safe|backend derived/.test(token)) return { key: "read-only", ...CANONICAL_STATUS_LANGUAGE["read-only"] };
    if (/live capital disabled|live capital off/.test(token)) return { key: "live-capital-off", ...CANONICAL_STATUS_LANGUAGE["live-capital-off"] };
    if (/paper/.test(token)) return { key: "paper-only", ...CANONICAL_STATUS_LANGUAGE["paper-only"] };
    if (/local only/.test(token)) return { key: "local-only", ...CANONICAL_STATUS_LANGUAGE["local-only"] };
    if (/non executable|research only|context only|prior only|challenge only/.test(token)) return { key: "non-executable", ...CANONICAL_STATUS_LANGUAGE["non-executable"] };
    if (/online|ok|ready|connected|available|active|configured|validated|certified|approved|passed|complete|written/.test(token)) return { key: "current", ...CANONICAL_STATUS_LANGUAGE.current };
    return {
        key: "raw-status",
        label: dashboardText(value, options.fallback || "Not exported"),
        tone: "pending",
        description: "Raw status value not yet mapped to the canonical dashboard language."
    };
}

function canonicalStatusLabel(value, options = {}) {
    const record = canonicalStatusRecord(value, options);
    return record ? record.label : dashboardText(value, options.fallback || "Not exported");
}

function canonicalStatusTone(value, fallback = "pending") {
    return canonicalStatusRecord(value, { fallback })?.tone || fallback;
}

function canonicalBadgeText(value) {
    return canonicalStatusRecord(value, { strict: true })?.label || dashboardText(value);
}

function htmlText(value, fallback = "Not connected yet") {
    return dashboardText(value, fallback).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;"
    })[char]);
}

function literalHtmlText(value, fallback = "Not connected yet") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;"
    })[char]);
}

function asArray(value) {
    return Array.isArray(value) ? value : [];
}

function statusClass(status) {
    const canonicalTone = canonicalStatusTone(status, status);
    return dashboardText(canonicalTone, "pending")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "") || "pending";
}

function normaliseCurrencyCode(value, fallback = "GBP") {
    const code = String(value || fallback || "GBP").trim().toUpperCase();
    return /^[A-Z]{3}$/.test(code) ? code : fallback;
}

function formatMoney(value, currency = "GBP") {
    const amount = Number(value || 0);
    return new Intl.NumberFormat("en-GB", {
        style: "currency",
        currency: normaliseCurrencyCode(currency),
        maximumFractionDigits: 0
    }).format(amount);
}

function capitalCurrency(capital = {}) {
    return normaliseCurrencyCode(capital.display_currency || capital.account_currency || "GBP");
}

function formatCapitalMoney(value, capital = {}) {
    return formatMoney(value, capitalCurrency(capital));
}

function formatUsd(value) {
    const amount = Number(value || 0);
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0
    }).format(amount);
}

function formatTime(value) {
    if (!value) return "Not connected";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Unknown";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit"
    }).format(date);
}

function formatLatency(value) {
    if (value === null || value === undefined || value === "") return "unknown";
    const latency = Number(value);
    if (Number.isNaN(latency)) return dashboardText(value, "unknown");
    return `${Math.round(latency)} ms`;
}

function countBy(items, key) {
    return asArray(items).reduce((acc, item) => {
        const value = item?.[key] || "unknown";
        acc[value] = (acc[value] || 0) + 1;
        return acc;
    }, {});
}

function sourceIsCore(source = {}) {
    return DASHBOARD_CORE_SOURCE_KEYS.has(String(source.source_key || ""));
}

function sourceDisplayStatus(source = {}) {
    const rawStatus = normalizeCanonicalStatusToken(source.status || "");
    const readiness = normalizeCanonicalStatusToken(source.readiness || "");
    const credentialStatus = normalizeCanonicalStatusToken(source.credential_status || "");
    if (rawStatus === "online") return "ok";
    if (rawStatus === "local only") return "local only";
    if (!sourceIsCore(source)) {
        return "optional";
    }
    if (credentialStatus === "missing" || readiness.includes("credential required")) {
        return "not configured";
    }
    if (rawStatus === "degraded") return "degraded";
    if (rawStatus === "pending") return "waiting";
    return source.status || "waiting";
}

function sourceRequiresAction(source = {}) {
    const displayStatus = canonicalStatusRecord(sourceDisplayStatus(source));
    return displayStatus?.tone === "degraded" || displayStatus?.tone === "blocked";
}

function setText(selector, value) {
    const target = dashboardQuery(selector);
    if (target) target.textContent = value;
}

function renderStatusPill(status) {
    const record = canonicalStatusRecord(status);
    return `<b class="node-status ${statusClass(record.tone)}" title="${htmlText(record.description)}">${htmlText(record.label)}</b>`;
}

function renderMetric(label, value) {
    return `<div class="metric"><span>${htmlText(label)}</span><strong>${htmlText(value)}</strong></div>`;
}

function renderInlineBadge(value, status = "pending") {
    return `<span class="inline-badge ${statusClass(status)}">${htmlText(canonicalBadgeText(value))}</span>`;
}

function renderPanelBrief({ id, question, state, tone = "pending", primary, secondary, boundary }) {
    return `
        <section class="panel-brief ${statusClass(tone)}" data-panel-brief="${htmlText(id)}">
            <div class="panel-brief-main">
                <p class="label">Panel readout</p>
                <h3>${htmlText(question)}</h3>
                <p>${htmlText(primary)}</p>
            </div>
            <dl class="panel-brief-facts">
                <div>
                    <dt>State</dt>
                    <dd>${renderInlineBadge(state, tone)}</dd>
                </div>
                <div>
                    <dt>Watch</dt>
                    <dd>${htmlText(secondary)}</dd>
                </div>
                <div>
                    <dt>Boundary</dt>
                    <dd>${htmlText(boundary)}</dd>
                </div>
            </dl>
        </section>
    `;
}

function replacePanelBrief(id, config) {
    const target = dashboardQuery(`[data-panel-brief="${id}"]`);
    if (target) target.outerHTML = renderPanelBrief({ id, ...config });
}

function renderTagList(items, emptyText = "None recorded") {
    const list = Array.isArray(items) ? items.filter(Boolean) : [];
    if (!list.length) return `<span>${htmlText(emptyText)}</span>`;
    return list.map((item) => `<span>${htmlText(item)}</span>`).join("");
}

function sumNestedItems(items, key) {
    return asArray(items).reduce((total, item) => total + asArray(item?.[key]).length, 0);
}

function compactUnique(items, limit = 12) {
    const seen = new Set();
    const values = [];
    asArray(items).forEach((item) => {
        const value = dashboardText(item, "").trim();
        if (!value || seen.has(value)) return;
        seen.add(value);
        values.push(value);
    });
    return values.slice(0, limit);
}

function formatConfidence(value) {
    if (value === null || value === undefined || value === "") return "unknown";
    const score = Number(value);
    if (Number.isNaN(score)) return dashboardText(value, "unknown");
    return score <= 1 ? `${Math.round(score * 100)}%` : `${Math.round(score)}%`;
}

function formatProbability(value) {
    if (value === null || value === undefined || value === "") return "unknown";
    const score = Number(value);
    if (Number.isNaN(score)) return dashboardText(value, "unknown");
    return score <= 1 ? `${Math.round(score * 100)}%` : `${Math.round(score)}%`;
}

function formatPercent(value) {
    if (value === null || value === undefined || value === "") return "0%";
    const score = Number(value);
    if (Number.isNaN(score)) return dashboardText(value, "0%");
    return `${score}%`;
}

function findModule(status, key) {
    return asArray(status.modules).find((module) => module.key === key);
}

const FLOW_NODE_DETAILS = {
    watching: {
        role: "Source desks",
        input: "Feeds, alerts, charts",
        output: "Observed facts",
        authority: "Observation only"
    },
    event_log: {
        role: "System memory",
        input: "Every material event",
        output: "Audit trail",
        authority: "Source of truth"
    },
    live_bridge: {
        role: "Read-only bridge",
        input: "Sanitized snapshot",
        output: "Dashboard status",
        authority: "No command route"
    },
    worldview: {
        role: "Prior assumptions",
        input: "World-model priors",
        output: "Sharper questions",
        authority: "Context only"
    },
    research_analyst: {
        role: "Research desk",
        input: "Noisy observations",
        output: "Shadow analysis",
        authority: "No execution"
    },
    strategy_lead: {
        role: "Strategy desk",
        input: "Evidence packets",
        output: "Challenge notes",
        authority: "Escalation only"
    },
    head_of_quant: {
        role: "Quant desk",
        input: "Bounded scenarios and Fire Opal/IBM readiness",
        output: "Oracle check and hardware gate status",
        authority: "Non-executable"
    },
    shadow_intelligence: {
        role: "Research queue",
        input: "Model packets",
        output: "Hypotheses",
        authority: "Research only"
    },
    execution_registry: {
        role: "Risk desk",
        input: "Trade intents",
        output: "Blocks or gates",
        authority: "Blocked unless safe"
    },
    staged_order_contract: {
        role: "Paper gate",
        input: "Execution-policy reviews",
        output: "Disabled staging checks",
        authority: "No orders"
    },
    broker_reconciliation: {
        role: "Broker gate",
        input: "Staged-order reviews",
        output: "Broker echo checks",
        authority: "Read-only; no submit"
    },
    trade_layer: {
        role: "Paper trading",
        input: "Approved intents",
        output: "Paper trade states",
        authority: "Live capital off"
    },
    telegram_bot: {
        role: "Member comms",
        input: "Status events",
        output: "Notifications",
        authority: "Notify only"
    },
    paper_account: {
        role: "Money mirror",
        input: "Paper broker state",
        output: "Balances and positions",
        authority: "Read-only"
    },
    postmortem_loop: {
        role: "Learning loop",
        input: "Closed paper trades",
        output: "Lessons and weight updates",
        authority: "After-action review"
    },
    fund_manager_forum: {
        role: "Governance desk",
        input: "Member comments",
        output: "Improvement notes",
        authority: "Governance only"
    }
};

function flowNodeDetails(module) {
    if (module?.role || module?.input || module?.output) {
        return {
            role: dashboardText(module?.role || module?.owner, "Qadam desk"),
            input: dashboardText(module?.input, "Runtime state"),
            output: dashboardText(module?.output, "Dashboard state"),
            authority: dashboardText(module?.authority, "read only")
        };
    }
    const key = module?.key || "";
    return FLOW_NODE_DETAILS[key] || {
        role: dashboardText(module?.owner, "Qadam desk"),
        input: "Runtime state",
        output: "Dashboard state",
        authority: dashboardText(module?.authority, "read only")
    };
}

function systemMapAuthorityLabel(module, details) {
    const value = details?.authority || module?.authority;
    const raw = String(value || "");
    if (/dry[_ ]run[_ ]notify[_ ]only/i.test(raw)) return "Dry-run; Notify only";
    if (/notify[_ ]only/i.test(raw)) return "Notify only";
    const fallback = FLOW_NODE_DETAILS[module?.key]?.authority;
    if (fallback && /_/.test(raw)) return fallback;
    return dashboardText(value, "read only");
}

function modelNumber(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
}

function latestItem(items) {
    const list = asArray(items);
    return list.length ? list[list.length - 1] : {};
}

function boolCountFlag(value) {
    return value === true || modelNumber(value, 0) > 0;
}

function normalizeModelHealth(value, authority = "") {
    const raw = String(value || authority || "pending").toLowerCase().replaceAll("_", "-");
    const rawAuthority = String(authority || "").toLowerCase().replaceAll("_", "-");
    if (raw.includes("blocked") || raw.includes("missing") || raw.includes("failed") || raw.includes("error")) return "blocked";
    if (rawAuthority.includes("blocked") || rawAuthority.includes("no-submit")) return "blocked";
    if (raw.includes("degraded") || raw.includes("stale")) return "degraded";
    if (raw.includes("read-only") || rawAuthority.includes("read-only") || raw === "ok" || raw.includes("ready")) return "read-only";
    if (raw.includes("local-only") || rawAuthority.includes("local-only")) return "local-only";
    if (raw.includes("supplemental") || rawAuthority.includes("supplemental")) return "supplemental";
    if (raw.includes("shadow") || rawAuthority.includes("shadow") || rawAuthority.includes("challenge-only")) return "shadow-only";
    if (raw.includes("online") || raw.includes("connected") || raw.includes("available")) return "online";
    if (raw.includes("pending") || raw.includes("deferred") || raw.includes("not-run")) return "pending";
    return "pending";
}

function dashboardModelEmptyState(key, count = 0, override = {}) {
    const states = {
        normal_no_setup: {
            title: "No qualified setup right now",
            body: "Qadam has not found a setup that meets the current source and risk requirements.",
            tone: "neutral"
        },
        normal_no_trade: {
            title: "No paper trade right now",
            body: "There is no active paper trade in the current dashboard status.",
            tone: "neutral"
        },
        normal_no_position: {
            title: "No open paper position",
            body: "The paper account has no open position in the current snapshot.",
            tone: "neutral"
        },
        normal_no_postmortem: {
            title: "No postmortem due",
            body: "There is no closed paper trade waiting for review.",
            tone: "neutral"
        },
        blocked: {
            title: "Safety stop",
            body: "Qadam is held by a safety, source, risk, or approval rule. The dashboard remains read-only and cannot bypass the stop.",
            tone: "blocked"
        },
        stale: {
            title: "Status may be stale",
            body: "The latest status is older than expected. Treat the readout as informational until the status refreshes.",
            tone: "warning"
        },
        degraded: {
            title: "Some inputs are degraded",
            body: "One or more feeds, models, or runtime checks are unavailable. Qadam should reduce confidence until the degraded input recovers.",
            tone: "warning"
        },
        missing: {
            title: "Missing setup",
            body: "The dashboard has no status for this panel yet. This does not create trading authority.",
            tone: "neutral"
        }
    };
    return {
        key,
        count,
        ...(states[key] || states.missing),
        ...override
    };
}

function collectAuthorityFlags(status) {
    const capital = status.capital || {};
    const tradeLayer = status.trade_layer || {};
    const phase5 = status.phase5_certification || {};
    const phase6 = status.phase6_learning_loop || {};
    const phase6Certification = status.phase6_certification || {};
    const phase7 = status.phase7_demo_proof || {};
    const phase5SystemMap = status.phase5_system_map || {};
    const checks = [
        ["capital.live_capital_enabled", capital.live_capital_enabled],
        ["capital.write_authority", capital.write_authority],
        ["trade_layer.execution_allowed_count", tradeLayer.summary?.execution_allowed_count],
        ["trade_layer.paper_order_allowed_count", tradeLayer.summary?.paper_order_allowed_count],
        ["phase5.live_capital_enabled_count", phase5.live_capital_enabled_count],
        ["phase5.broker_write_allowed_count", phase5.broker_write_allowed_count],
        ["phase6.live_capital_enabled", phase6.live_capital_enabled],
        ["phase6.broker_write_allowed", phase6.broker_write_allowed],
        ["phase6.phase7_proof_credit_allowed", phase6.phase7_proof_credit_allowed],
        ["phase6_certification.live_capital_enabled", phase6Certification.live_capital_enabled],
        ["phase6_certification.broker_write_allowed", phase6Certification.broker_write_allowed],
        ["phase6_certification.phase7_proof_credit_allowed", phase6Certification.phase7_proof_credit_allowed],
        ["phase7.live_capital_enabled", phase7.live_capital_enabled],
        ["phase7.phase7_proof_credit_allowed", phase7.phase7_proof_credit_allowed],
        ["phase5_system_map.guardrails.live_capital_enabled", phase5SystemMap.guardrails?.live_capital_enabled]
    ];
    return checks
        .filter(([, value]) => boolCountFlag(value))
        .map(([key]) => key);
}

function collectReadinessWarnings(status) {
    const phase6 = status.phase6_learning_loop || {};
    const phase6Certification = status.phase6_certification || {};
    const phase7 = status.phase7_demo_proof || {};
    const phase5SystemMap = status.phase5_system_map || {};
    const warnings = [];
    if (status.generated_at) {
        const generatedAt = new Date(status.generated_at).getTime();
        if (Number.isFinite(generatedAt) && Date.now() - generatedAt > 60 * 60 * 1000) {
            warnings.push("stale_status");
        }
    }
    const uiInferredCount = [
        phase6.ui_inferred_readiness_count,
        phase6Certification.cockpit_ui_inferred_readiness_count,
        phase7.ui_inferred_readiness_count,
        phase5SystemMap.ui_inferred_node_count
    ].reduce((total, value) => total + modelNumber(value, 0), 0);
    if (uiInferredCount > 0 || phase7.display_derived_from_backend === false || phase6.display_derived_from_backend === false) {
        warnings.push("ui_inferred_readiness_detected");
    }
    const canonical = phase5SystemMap.source_posture?.canonical || status.durable_ingestion || {};
    const expected = modelNumber(canonical.expected_source_count, modelNumber(canonical.durable_expected_source_count, 0));
    const replayed = modelNumber(canonical.replayed_source_count, modelNumber(canonical.durable_replayed_source_count, 0));
    const missing = modelNumber(canonical.missing_source_count, Math.max(0, expected - replayed));
    if (expected && (missing > 0 || replayed < expected)) warnings.push("missing_source_quorum");
    const proofAllowed = Boolean(phase7.phase7_proof_credit_allowed);
    const proofCount = modelNumber(phase7.closed_proof_trade_count, 0);
    const proofTarget = modelNumber(phase7.mature_benchmark, 100);
    const completedDays = modelNumber(phase7.completed_calendar_day_count, 0);
    const requiredDays = modelNumber(phase7.phase7_harness_day_count, 30);
    if (proofAllowed && (proofCount < proofTarget || completedDays < requiredDays)) {
        warnings.push("false_phase7_proof_credit");
    }
    return warnings;
}

function buildSourcesModel(status = {}) {
    const watching = asArray(status.watching);
    const displaySources = watching.map((source) => ({
        ...source,
        core: sourceIsCore(source),
        display_status: sourceDisplayStatus(source),
        requires_action: sourceRequiresAction(source)
    }));
    const pipelineSummary = asArray(status.source_pipeline_summary);
    const cognition = status.cognition || {};
    const sourceCounts = countBy(displaySources, "display_status");
    const durable = status.durable_ingestion || status.mission_control?.durable_spine || {};
    const phase5SystemMap = status.phase5_system_map || {};
    const canonical = phase5SystemMap.source_posture?.canonical || durable;
    const expected = modelNumber(canonical.expected_source_count, modelNumber(durable.expected_source_count, 0));
    const replayed = modelNumber(canonical.replayed_source_count, modelNumber(durable.replayed_source_count, 0));
    const missing = modelNumber(canonical.missing_source_count, Math.max(0, expected - replayed));
    const missingCredentialSources = displaySources.filter(
        (source) => source.core && source.credential_status === "missing"
    );
    const optionalCredentialSources = displaySources.filter(
        (source) => !source.core && source.credential_status === "missing"
    );
    const degraded = displaySources.filter((source) => source.requires_action).length;
    const pending = modelNumber(sourceCounts.waiting, 0);
    const optional = modelNumber(sourceCounts.optional, 0);
    const localOnly = modelNumber(sourceCounts["local only"], 0);
    const online = modelNumber(sourceCounts.ok, 0);
    const coreSourceCount = displaySources.filter((source) => source.core).length;
    const coreOkCount = displaySources.filter((source) => source.core && source.display_status === "ok").length;
    const missingCredentialCount = missingCredentialSources.length;
    const pendingAdapterSources = displaySources.filter((source) => !source.promoted_adapter || String(source.registry_status || "").includes("ready_to_build"));
    const generatedAtMs = Date.parse(status.generated_at || "");
    const staleHeartbeatSources = watching.filter((source) => {
        const heartbeatMs = Date.parse(source.last_heartbeat || "");
        if (!heartbeatMs) return true;
        if (!generatedAtMs) return false;
        return generatedAtMs - heartbeatMs > 36 * 60 * 60 * 1000;
    });
    const summaryByPipeline = new Map(pipelineSummary.map((pipeline) => [pipeline.pipeline, pipeline]));
    const pipelineRecords = Object.entries(displaySources.reduce((acc, source) => {
        const pipeline = source.pipeline || "unknown";
        acc[pipeline] = acc[pipeline] || [];
        acc[pipeline].push(source);
        return acc;
    }, {}))
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([pipeline, sources]) => {
            const counts = countBy(sources, "display_status");
            const pipelineCounts = summaryByPipeline.get(pipeline) || {};
            const signalInfluencing = sources.filter((source) => source.can_influence_signals).length;
            const requiresAction = sources.some((source) => source.requires_action);
            const hasOk = sources.some((source) => source.display_status === "ok");
            const hasWaiting = sources.some((source) => source.display_status === "waiting");
            return {
                pipeline,
                label: dashboardText(pipeline),
                source_count: sources.length,
                online_count: modelNumber(counts.ok, 0),
                degraded_count: modelNumber(counts.degraded, 0),
                pending_count: modelNumber(counts.waiting, 0),
                optional_count: modelNumber(counts.optional, 0),
                local_only_count: modelNumber(pipelineCounts.local_only_count || counts.local_only || counts["local-only"], 0),
                missing_credential_count: sources.filter((source) => source.core && source.credential_status === "missing").length,
                pending_adapter_count: sources.filter((source) => !source.promoted_adapter).length,
                signal_influencing_count: signalInfluencing,
                status: requiresAction
                    ? "degraded"
                    : (hasOk ? "ok" : (hasWaiting ? "waiting" : "optional")),
                top_sources: sources
                    .slice()
                    .sort((a, b) => String(a.source_name).localeCompare(String(b.source_name)))
                    .slice(0, 4)
                    .map((source) => ({
                        key: source.source_key,
                        label: source.source_name || source.source_key,
                        status: source.display_status,
                        readiness: source.readiness,
                        credential_status: source.credential_status,
                        promoted_adapter: Boolean(source.promoted_adapter),
                        can_influence_signals: Boolean(source.can_influence_signals),
                        heartbeat: source.last_heartbeat
                    })),
                sources: sources
                    .slice()
                    .sort((a, b) => String(a.source_name || a.source_key).localeCompare(String(b.source_name || b.source_key)))
                    .map((source) => ({
                        key: source.source_key,
                        label: source.source_name || source.source_key,
                        pipeline: source.pipeline || pipeline,
                        status: source.display_status,
                        raw_status: source.raw_status || source.status || "pending",
                        readiness: source.readiness || source.registry_status || "not exported",
                        credential_status: source.credential_status || "not exported",
                        auth_class: source.auth_class || "not exported",
                        cadence: source.cadence || "cadence unknown",
                        tier: source.tier || "n/a",
                        trust_score: source.trust_score,
                        promoted_adapter: Boolean(source.promoted_adapter),
                        can_influence_signals: Boolean(source.can_influence_signals),
                        heartbeat: source.last_heartbeat,
                        payload_time: source.last_payload_time,
                        degraded_reason: source.degraded_reason || null,
                        influence_boundary: source.influence_boundary || "blocked until signal integrity gate"
                    }))
            };
        });
    const supplemental = [
        {
            key: "yahoo_finance",
            label: "Yahoo Finance",
            status: status.yahoo_finance?.enabled
                ? (status.yahoo_finance?.status || phase5SystemMap.source_posture?.yahoo_finance?.status || "not exported")
                : "optional",
            role: status.yahoo_finance?.market_confirmation_role || phase5SystemMap.source_posture?.yahoo_finance?.role || "supplemental market confirmation only",
            authority: "read-only supplemental",
            capability_state: status.yahoo_finance?.enabled ? "live read configured" : "optional",
            provenance_status: status.yahoo_finance?.sample_mode_available ? "sample mode available" : "sample mode missing",
            degraded: Boolean(status.yahoo_finance?.enabled && status.yahoo_finance?.degraded),
            proof_boundary: "Supplemental confirmation only; not source quorum, signal, order, broker, receipt, or reconciliation truth."
        },
        {
            key: "preference_mcp",
            label: "Preference MCP",
            status: status.preference_mcp?.enabled
                ? (status.preference_mcp?.status || phase5SystemMap.source_posture?.preference_mcp?.status || "not exported")
                : "optional",
            role: status.preference_mcp?.classification || "supplemental challenge context",
            authority: "challenge-only supplemental",
            capability_state: status.preference_mcp?.enabled ? "live MCP configured" : "optional",
            provenance_status: status.preference_mcp?.provenance_status || "not verified",
            degraded: Boolean(status.preference_mcp?.enabled && status.preference_mcp?.degraded),
            proof_boundary: "Challenge-only supplemental data plane; not source quorum, trade authority, paid-tool authority, broker write, or live capital."
        }
    ];
    const observedSignals = asArray(status.trade_layer?.watching);
    const candidates = asArray(status.trade_layer?.candidates);
    const evidencePackets = asArray(cognition.evidence_packets);
    const phase7 = status.phase7_demo_proof || {};
    const sourceSetupLinks = [
        ...observedSignals.map((signal) => ({
            kind: "observed_signal",
            label: signal.instrument || signal.symbol || "Observed signal",
            stage: "Observed signal",
            source_ref: signal.source || signal.source_type || "source not exported",
            status: signal.status || "observed_signal",
            href: "#trade-layer",
            summary: signal.trigger || signal.chart_context || "Observed source event.",
            proof_boundary: "Observed source event only; not a candidate or order."
        })),
        ...candidates.map((candidate) => ({
            kind: "candidate",
            label: candidate.instrument || candidate.strategy || "Trade idea",
            stage: "Trade idea",
            source_ref: candidate.source_signal_id || candidate.source_type || "source signal not exported",
            status: candidate.status || "candidate",
            href: "#trade-layer",
            summary: candidate.evidence_summary || candidate.catalyst || "Trade-idea evidence pending.",
            proof_boundary: "A trade idea needs corroboration, Strategy Lead review, and risk gates before paper trading."
        })),
        modelNumber(phase7.candidate_setup_count, 0) ? {
            kind: "qualified_setup_pool",
            label: "Paper growth setup pool",
            stage: modelNumber(phase7.eligible_setup_count, 0) ? "Potential setup available" : "Candidate setup not eligible",
            source_ref: "phase7_qualified_setup_ledger",
            status: phase7.proof_state || "ready_no_closed_trades",
            href: "#trades",
            summary: `${modelNumber(phase7.candidate_setup_count, 0)} candidate setups and ${modelNumber(phase7.eligible_setup_count, 0)} potential paper setups exported by backend status.`,
            proof_boundary: "Setup visibility is not verified performance and cannot create an order."
        } : null
    ].filter(Boolean);
    const tone = missing || missingCredentialCount || degraded ? "degraded" : (watching.length ? "online" : "pending");
    const evidencePacketCards = evidencePackets.slice(0, 5).map((packet) => {
        const items = asArray(packet.items);
        const itemSources = items
            .map((item) => item.source)
            .filter(Boolean)
            .slice(0, 3);
        return {
            trail_id: dashboardText(packet.trail_id, packet.signal_id || "evidence_packet"),
            signal_id: dashboardText(packet.signal_id, "signal not linked"),
            status: dashboardText(packet.status, items.length ? "evidence_recorded" : "pending"),
            item_count: items.length,
            summary: dashboardText(
                packet.summary || items[0]?.summary,
                "Factual evidence packet exported from the research queue."
            ),
            sources: itemSources.length ? itemSources.join(", ") : "sources not exported",
            boundary: "Factual evidence can support review, but cannot create trade ideas, orders, broker writes, or performance credit."
        };
    });
    const reviewGroups = [
        {
            id: "setup_evidence",
            label: "Setup evidence",
            summary: "Observed signals, trade ideas, and setup-pool records tied back to source refs.",
            record_count: sourceSetupLinks.length,
            tone: sourceSetupLinks.length ? "pending" : "online"
        },
        {
            id: "source_reliability",
            label: "Source reliability",
            summary: "Credential, heartbeat, adapter, and quorum state by intelligence pipeline.",
            record_count: pipelineRecords.length,
            tone: missing || missingCredentialCount || degraded ? "degraded" : "online"
        },
        {
            id: "supplemental_context",
            label: "Supplemental context",
            summary: "Yahoo Finance and Preference/PREF are confirmation/challenge-only context.",
            record_count: supplemental.length,
            tone: supplemental.some((source) => source.degraded) ? "degraded" : "pending"
        },
        {
            id: "factual_packets",
            label: "Factual evidence packets",
            summary: "Research packets stay separate from priors and still require corroboration.",
            record_count: evidencePacketCards.length,
            tone: evidencePacketCards.length ? "online" : "pending"
        }
    ];
    return {
        id: "sources",
        label: "Evidence",
        question: "Are Qadam's inputs fresh, trustworthy, and sufficient?",
        tone,
        summary: `${coreOkCount}/${coreSourceCount} core sources OK; ${missing} canonical sources missing; ${missingCredentialCount} required credentials missing; ${optionalCredentialSources.length} optional credentials not configured; ${evidencePacketCards.length} factual evidence packets visible.`,
        counts: {
            total: watching.length,
            online,
            degraded,
            pending,
            optional,
            core: coreSourceCount,
            core_ok: coreOkCount,
            local_only: localOnly,
            missing_credentials: missingCredentialCount,
            optional_credentials: optionalCredentialSources.length,
            signal_influencing: watching.filter((source) => source.can_influence_signals).length,
            pipelines: pipelineSummary.length,
            supplemental: supplemental.length,
            source_setup_links: sourceSetupLinks.length,
            evidence_packets: evidencePacketCards.length
        },
        reliability: [
            { key: "core_ok", label: "Core OK", count: `${coreOkCount}/${coreSourceCount}`, tone: coreOkCount === coreSourceCount ? "online" : "pending", detail: "Required paper-trading source feeds reporting healthy status." },
            { key: "needs_attention", label: "Needs attention", count: degraded, tone: degraded ? "degraded" : "online", detail: "Required sources with degraded runtime state." },
            { key: "missing_credential", label: "Required not configured", count: missingCredentialSources.length, tone: missingCredentialSources.length ? "degraded" : "online", detail: "Required source credentials not configured." },
            { key: "stale_heartbeat", label: "Stale heartbeat", count: staleHeartbeatSources.length, tone: staleHeartbeatSources.length ? "degraded" : "online", detail: "Sources missing heartbeat freshness in this snapshot." },
            { key: "optional", label: "Optional", count: optional, tone: "pending", detail: "Useful extra feeds that are not required for the current paper-trading core." },
            { key: "optional_credentials", label: "Optional not configured", count: optionalCredentialSources.length, tone: "pending", detail: "Optional feeds that can be wired later without blocking the core dashboard." },
            { key: "pending_adapter", label: "Adapter backlog", count: pendingAdapterSources.length, tone: pendingAdapterSources.length ? "pending" : "online", detail: "Sources that are registry-ready, derived, or not yet promoted adapters." }
        ],
        quorum: {
            expected_source_count: expected,
            replayed_source_count: replayed,
            missing_source_count: missing,
            status: missing || (expected && replayed < expected) ? "degraded" : "ok"
        },
        pipelines: pipelineRecords,
        all_sources: displaySources
            .slice()
            .sort((a, b) => String(a.source_name || a.source_key).localeCompare(String(b.source_name || b.source_key)))
            .map((source) => ({
                key: source.source_key,
                label: source.source_name || source.source_key,
                pipeline: source.pipeline || "unknown",
                status: source.display_status,
                raw_status: source.raw_status || source.status || "pending",
                readiness: source.readiness || source.registry_status || "not exported",
                credential_status: source.credential_status || "not exported",
                auth_class: source.auth_class || "not exported",
                cadence: source.cadence || "cadence unknown",
                tier: source.tier || "n/a",
                trust_score: source.trust_score,
                promoted_adapter: Boolean(source.promoted_adapter),
                can_influence_signals: Boolean(source.can_influence_signals),
                heartbeat: source.last_heartbeat,
                payload_time: source.last_payload_time,
                degraded_reason: source.degraded_reason || null,
                influence_boundary: source.influence_boundary || "blocked until signal integrity gate"
            })),
        supplemental,
        evidence_packets: evidencePacketCards,
        evidence_review_groups: reviewGroups,
        source_setup_links: sourceSetupLinks,
        source_to_setup_summary: sourceSetupLinks.length
            ? `${sourceSetupLinks.length} source-linked observed/trade-idea/setup records need corroboration review.`
            : "No active source-linked setup or trade-idea records are exported.",
        empty_state: watching.length ? null : dashboardModelEmptyState("missing"),
        boundary: "Sources create observations only. Supplemental sources cannot be sole proof and no source can create trade ideas, orders, broker writes, or live-capital authority."
    };
}

function firstPresent(...values) {
    return values.find((value) => value !== null && value !== undefined && value !== "");
}

function tradeLifecycleFilters(kind, item = {}) {
    const filters = new Set(["all"]);
    const status = String(item.status || item.postmortem_status || kind || "").toLowerCase();
    if (kind === "blocked" || status.includes("blocked")) filters.add("blocked");
    if (kind === "open_position" || status.includes("open")) filters.add("open");
    if (kind === "closed_paper_trade" || status.includes("closed") || status.includes("filled")) filters.add("closed");
    if (kind === "postmortem_due" || status.includes("postmortem_due")) filters.add("postmortem_due");
    if (!filters.has("blocked") && !filters.has("closed") && !filters.has("postmortem_due")) filters.add("active");
    return Array.from(filters);
}

function tradeLifecycleRecord(kind, item = {}, index = 0, options = {}) {
    const stageLabels = {
        observed_signal: "Observed signal",
        qualified_setup: "Qualified setup",
        candidate: "Trade idea",
        blocked: "Blocked idea",
        draft_paper_order: "Draft paper order",
        submitted_paper_order: "Submitted paper order",
        open_position: "Open position",
        closed_paper_trade: "Closed paper trade",
        postmortem_due: "Postmortem due"
    };
    const status = firstPresent(item.status, item.postmortem_status, options.status, kind);
    const title = firstPresent(
        item.instrument,
        item.symbol,
        item.strategy_family_key,
        item.order_id,
        item.trade_id,
        options.title,
        stageLabels[kind]
    );
    const summary = firstPresent(
        item.catalyst,
        item.trigger,
        item.evidence_summary,
        item.boundary,
        item.close_reason,
        options.summary,
        `${stageLabels[kind]} record.`
    );
    const tone = options.tone || (
        kind === "blocked" || kind === "postmortem_due" ? "blocked"
            : (kind === "candidate" || kind === "draft_paper_order" ? "pending" : "online")
    );
    return {
        id: firstPresent(item.intent_id, item.alert_id, item.order_id, item.trade_id, `${kind}_${index + 1}`),
        kind,
        stage_label: stageLabels[kind] || dashboardText(kind),
        title,
        status,
        tone,
        summary,
        instrument: firstPresent(item.instrument, item.symbol, "not specified"),
        direction: firstPresent(item.direction, "not specified"),
        observed_at: firstPresent(item.observed_at, item.created_at, item.submitted_at, item.opened_at, item.closed_at, item.updated_at),
        filters: tradeLifecycleFilters(kind, item),
        proof_scope: options.proof_scope || "phase5_test_lifecycle",
        proof_scope_label: options.proof_scope_label || "Phase 5 test lifecycle",
        phase7_proof_credit_allowed: false,
        source_quorum_status: options.source_quorum_status || "not exported",
        risk_decision: firstPresent(item.risk_state, item.blocked_reason, item.status, options.risk_decision, "not reviewed"),
        broker_receipt_status: options.broker_receipt_status || "not present",
        references: options.references || [],
        boundary: firstPresent(item.boundary, options.boundary, "Lifecycle display is read-only. A trade idea is not an order.")
    };
}

function tradeLifecycleCountRecord(kind, count, options = {}) {
    if (!count) return null;
    return tradeLifecycleRecord(kind, {
        status: options.status || "backend_count",
        instrument: options.title,
        boundary: options.boundary,
        risk_state: options.risk_decision
    }, 0, {
        ...options,
        summary: `${count} ${options.summary_label || options.title || "records"} reported by backend status.`,
        proof_scope: options.proof_scope || "phase7_demo_proof",
        proof_scope_label: options.proof_scope_label || "Verified paper-trading setup"
    });
}

function buildTradesModel(status = {}, sharedModels = {}) {
    const tradeLayer = status.trade_layer || {};
    const capital = status.capital || {};
    const phase7 = status.phase7_demo_proof || {};
    const phase5Drill = status.phase5_paper_trade_drill || {};
    const sourceModel = sharedModels.sources_model || buildSourcesModel(status);
    const observed = asArray(tradeLayer.watching);
    const candidates = asArray(tradeLayer.candidates);
    const blocked = asArray(tradeLayer.blocked);
    const staged = asArray(tradeLayer.staged_orders);
    const submitted = asArray(tradeLayer.submitted_orders);
    const orders = asArray(capital.orders);
    const submittedLifecycle = [...submitted, ...orders];
    const openPositions = asArray(capital.open_positions);
    const closedTrades = asArray(capital.closed_trades);
    const postmortemsDue = asArray(capital.postmortems_due);
    const proofCreditSafe = Boolean(phase7.phase7_proof_credit_allowed)
        && modelNumber(phase7.closed_proof_trade_count, 0) >= modelNumber(phase7.mature_benchmark, 100)
        && modelNumber(phase7.completed_calendar_day_count, 0) >= modelNumber(phase7.phase7_harness_day_count, 30);
    const lifecycle = [
        { key: "observed_signal", label: "Observed signals", count: observed.length, tone: observed.length ? "online" : "pending" },
        { key: "qualified_setup", label: "Qualified setups", count: modelNumber(phase7.eligible_setup_count, 0), tone: modelNumber(phase7.eligible_setup_count, 0) ? "online" : "pending" },
        { key: "candidate", label: "Trade ideas", count: candidates.length, tone: candidates.length ? "pending" : "online" },
        { key: "blocked", label: "Blocked ideas", count: blocked.length, tone: blocked.length ? "blocked" : "online" },
        { key: "draft_paper_order", label: "Draft paper orders", count: staged.length, tone: staged.length ? "pending" : "online" },
        { key: "submitted_paper_order", label: "Submitted paper orders", count: submittedLifecycle.length, tone: submittedLifecycle.length ? "online" : "pending" },
        { key: "open_position", label: "Open positions", count: openPositions.length, tone: openPositions.length ? "online" : "pending" },
        { key: "closed_paper_trade", label: "Closed paper trades", count: closedTrades.length, tone: closedTrades.length ? "online" : "pending" },
        { key: "postmortem_due", label: "Postmortems due", count: postmortemsDue.length, tone: postmortemsDue.length ? "blocked" : "online" }
    ];
    const sourceQuorumStatus = sourceModel.quorum.status;
    const baseReferences = [
        {
            label: "Source quorum",
            href: "#evidence",
            status: sourceQuorumStatus
        }
    ];
    const riskReference = {
        label: "Risk decision",
        href: "#trade-risk-policy",
        status: status.risk_agent?.status || tradeLayer.risk_agent?.status || "not reviewed"
    };
    const brokerReference = {
        label: "Broker receipt",
        href: "#trade-broker-receipts",
        status: phase5Drill.broker_receipt_count ? "receipt visible" : "not present"
    };
    const lifecycleRecords = [
        ...observed.map((item, index) => tradeLifecycleRecord("observed_signal", item, index, {
            source_quorum_status: sourceQuorumStatus,
            references: baseReferences
        })),
        tradeLifecycleCountRecord("qualified_setup", modelNumber(phase7.candidate_setup_count, 0), {
            title: "Paper-trading setup pool",
            status: phase7.eligible_setup_count ? "eligible_setup_available" : "candidate_setup_not_eligible",
            tone: phase7.eligible_setup_count ? "online" : "pending",
            summary_label: "candidate setups",
            risk_decision: "awaiting proof eligibility",
            source_quorum_status: sourceQuorumStatus,
            references: baseReferences,
            boundary: "Candidate setup count is not verified performance and cannot create an order."
        }),
        ...candidates.map((item, index) => tradeLifecycleRecord("candidate", item, index, {
            source_quorum_status: sourceQuorumStatus,
            references: [...baseReferences, riskReference]
        })),
        ...blocked.map((item, index) => tradeLifecycleRecord("blocked", item, index, {
            source_quorum_status: sourceQuorumStatus,
            references: [...baseReferences, riskReference]
        })),
        ...staged.map((item, index) => tradeLifecycleRecord("draft_paper_order", item, index, {
            source_quorum_status: sourceQuorumStatus,
            references: [...baseReferences, riskReference, brokerReference]
        })),
        ...submittedLifecycle.map((item, index) => tradeLifecycleRecord("submitted_paper_order", item, index, {
            tone: "online",
            source_quorum_status: sourceQuorumStatus,
            broker_receipt_status: phase5Drill.broker_receipt_count ? "broker receipt mirrored" : "not present",
            references: [...baseReferences, riskReference, brokerReference]
        })),
        ...openPositions.map((item, index) => tradeLifecycleRecord("open_position", item, index, {
            tone: "online",
            source_quorum_status: sourceQuorumStatus,
            references: [...baseReferences, brokerReference]
        })),
        ...closedTrades.map((item, index) => tradeLifecycleRecord("closed_paper_trade", item, index, {
            tone: "online",
            source_quorum_status: sourceQuorumStatus,
            broker_receipt_status: phase5Drill.broker_receipt_count ? "broker receipt mirrored" : "not present",
            references: [...baseReferences, brokerReference]
        })),
        ...postmortemsDue.map((item, index) => tradeLifecycleRecord("postmortem_due", item, index, {
            tone: "blocked",
            source_quorum_status: sourceQuorumStatus,
            broker_receipt_status: phase5Drill.broker_receipt_count ? "broker receipt mirrored" : "not present",
            references: [...baseReferences, brokerReference]
        }))
    ].filter(Boolean);
    return {
        id: "trades",
        label: "Trades",
        question: "What happened to setups, trade ideas, orders, positions, exits, and postmortems?",
        tone: blocked.length || postmortemsDue.length ? "blocked" : (candidates.length || submitted.length || closedTrades.length ? "pending" : "online"),
        summary: `${observed.length} observed signals, ${candidates.length} trade ideas, ${submittedLifecycle.length} submitted paper orders, ${openPositions.length} open positions, ${closedTrades.length} closed paper trades.`,
        counts: {
            observed_signal: observed.length,
            qualified_setup: modelNumber(phase7.eligible_setup_count, 0),
            candidate: candidates.length,
            blocked: blocked.length,
            draft_paper_order: staged.length,
            submitted_paper_order: submittedLifecycle.length,
            open_position: openPositions.length,
            closed_paper_trade: closedTrades.length,
            postmortem_due: postmortemsDue.length
        },
        lifecycle,
        lifecycle_records: lifecycleRecords,
        lifecycle_filters: TRADE_WORKSPACE_FILTERS.map((filter) => ({
            ...filter,
            count: filter.id === "all"
                ? lifecycleRecords.length
                : lifecycleRecords.filter((record) => asArray(record.filters).includes(filter.id)).length
        })),
        proof_partitions: {
            phase5_test_lifecycle: {
                label: "Phase 5 test lifecycle",
                record_count: lifecycleRecords.filter((record) => record.proof_scope === "phase5_test_lifecycle").length,
                submitted_paper_order_count: modelNumber(phase5Drill.submitted_paper_order_count, submittedLifecycle.length),
                broker_receipt_count: modelNumber(phase5Drill.broker_receipt_count, 0),
                open_position_count: modelNumber(phase5Drill.open_position_count, openPositions.length),
                closed_trade_count: modelNumber(phase5Drill.closed_trade_count, closedTrades.length),
                postmortem_due_count: modelNumber(phase5Drill.postmortem_due_count, postmortemsDue.length),
                counts_for_phase7_proof: false
            },
            phase7_demo_proof: {
                label: "Verified paper trades",
                record_count: lifecycleRecords.filter((record) => record.proof_scope === "phase7_demo_proof").length,
                qualified_setup_count: modelNumber(phase7.qualified_setup_count, 0),
                eligible_setup_count: modelNumber(phase7.eligible_setup_count, 0),
                staged_proof_order_count: modelNumber(phase7.staged_proof_order_count, 0),
                submitted_paper_order_count: modelNumber(phase7.submitted_paper_order_count, 0),
                broker_receipt_count: modelNumber(phase7.broker_receipt_count, 0),
                open_position_count: modelNumber(phase7.open_position_count, 0),
                closed_proof_trade_count: modelNumber(phase7.closed_proof_trade_count, 0),
                postmortem_due_count: modelNumber(phase7.postmortem_due_count, 0),
                proof_credit_allowed: proofCreditSafe
            }
        },
        evidence_links: {
            source_quorum: baseReferences[0],
            risk_decision: riskReference,
            broker_receipt: brokerReference
        },
        consolidated_review_groups: [
            {
                id: "proof_lifecycle",
                label: "Paper trade lifecycle",
                summary: "Paper drill, certification state, learning handoff, and verified performance visibility."
            },
            {
                id: "gate_chain",
                label: "Gate chain and broker readiness",
                summary: "Signal review, risk policy, execution policy, staging, reconciliation, and dry-run receipt readiness."
            },
            {
                id: "signal_records",
                label: "Signals, trade ideas, and paper trades",
                summary: "TradingView observations, trade-idea records, blocked ideas, and explicit paper lifecycle states."
            }
        ],
        proof_credit: {
            backend_reported_allowed: Boolean(phase7.phase7_proof_credit_allowed),
            display_allowed: proofCreditSafe,
            closed_proof_trade_count: modelNumber(phase7.closed_proof_trade_count, 0),
            mature_benchmark: modelNumber(phase7.mature_benchmark, 100),
            phase5_test_trades_count_for_phase7: Boolean(phase7.phase5_test_trades_count_for_phase7)
        },
        model_dependencies: {
            sources_model: sourceModel.id || "sources"
        },
        empty_state: observed.length || candidates.length || submittedLifecycle.length || openPositions.length || closedTrades.length
            ? null
            : dashboardModelEmptyState("normal_no_trade"),
        boundary: tradeLayer.boundary || "A trade idea is not an order. Live capital stays disabled; only explicit paper trade state counts."
    };
}

function buildReasoningModel(status = {}) {
    const cognition = status.cognition || {};
    const philosophy = status.decision_philosophy || {};
    const phase4 = phase4StrategyStatus(status);
    const quantum = status.quantum_oracle || {};
    const hypotheses = asArray(cognition.hypotheses);
    const executableHypotheses = hypotheses.filter((hypothesis) => hypothesis.execution_allowed);
    const researchGoalState = cognition.research_goals || {};
    const researchGoals = asArray(cognition.research_goal_records || researchGoalState.recent_goals);
    const evidencePackets = asArray(cognition.evidence_packets);
    const shadowPackets = asArray(cognition.shadow_packets);
    const localResearch = asArray(cognition.local_research_assessments);
    const strategyPackets = asArray(cognition.strategy_lead_packets);
    const signalIntegrity = cognition.signal_integrity || {};
    const signalReviews = asArray(cognition.signal_integrity_reviews);
    const latestAssessment = localResearch[localResearch.length - 1] || {};
    const latestStrategyPacket = strategyPackets[strategyPackets.length - 1] || {};
    const latestStrategyReview = latestStrategyPacket.strategy_review || {};
    const latestSignalReview = signalReviews[signalReviews.length - 1] || {};
    const quantumRouting = quantum.latest_output_routing || {};
    const fireOpalIbm = status.qctrl_fire_opal_ibm_readiness || quantum.fire_opal_ibm_readiness || {};
    const evidenceBySignal = evidencePackets.reduce((acc, packet) => {
        if (packet.signal_id) acc[packet.signal_id] = packet;
        return acc;
    }, {});
    const worldviewLenses = asArray(philosophy.active_lenses).map((lens) => ({
        key: dashboardText(lens.key, "private_prior"),
        claim_type: dashboardText(lens.claim_type, "worldview_prior"),
        claim: dashboardText(lens.claim, "Private prior is not exported."),
        mechanism: dashboardText(lens.mechanism, "Mechanism not exported."),
        observable_signatures: asArray(lens.observable_signatures).slice(0, 4),
        live_sources_to_check: asArray(lens.live_sources_to_check).slice(0, 6),
        market_channels: asArray(lens.market_channels).slice(0, 6),
        corroboration_status: dashboardText(lens.corroboration_status, "prior_only"),
        evidence_boundary: dashboardText(
            lens.evidence_boundary || philosophy.boundary,
            "Prior, not evidence; it needs live-source corroboration."
        ),
        evidence_role: "prior_not_evidence",
        is_evidence: false,
        trade_authority: false
    }));
    const hypothesisQueue = hypotheses.slice(0, 5).map((hypothesis) => {
        const packet = evidenceBySignal[hypothesis.signal_id] || {};
        const missing = compactUnique([
            ...asArray(hypothesis.missing_correlations),
            ...asArray(packet.missing_correlations)
        ], 6);
        return {
            signal_id: dashboardText(hypothesis.signal_id, "shadow_hypothesis"),
            title: dashboardText(hypothesis.title, "Shadow hypothesis"),
            thesis: dashboardText(hypothesis.thesis, "No thesis exported."),
            instrument_focus: dashboardText(hypothesis.instrument_focus, "instrument watchlist"),
            status: dashboardText(hypothesis.status, "shadow_only"),
            advancement_state: hypothesis.execution_allowed
                ? "unexpected_executable_flag"
                : (missing.length ? "stalled_missing_corroboration" : "blocked_before_trade_layer"),
            advanced_by: `${modelNumber(hypothesis.evidence_source_count, 0)} evidence sources and ${dashboardText(hypothesis.generated_by, "deterministic triage")}`,
            stalled_by: missing.length ? missing.join(", ") : dashboardText(hypothesis.blocked_reason, "trade layer not reached"),
            blocked_reason: dashboardText(hypothesis.blocked_reason, "trade layer not reached"),
            confidence: hypothesis.confidence,
            integrity_review_status: dashboardText(hypothesis.integrity_review_status, "not reviewed"),
            integrity_score: hypothesis.integrity_score,
            evidence_packet_id: dashboardText(hypothesis.evidence_packet_id, "not linked"),
            evidence_source_count: modelNumber(hypothesis.evidence_source_count, 0),
            missing_corroboration: missing,
            invalidation: dashboardText(hypothesis.invalidation, "No invalidation recorded."),
            created_at: hypothesis.created_at,
            is_trade_candidate: false,
            paper_order_allowed: false,
            order_authority: false,
            boundary: "Hypothesis, not trade idea. It cannot stage orders, write brokers, or enable live capital."
        };
    });
    const researchGoalQueue = researchGoals.slice(0, 6).map((goal) => ({
        goal_id: dashboardText(goal.goal_id, "research_goal"),
        status: dashboardText(goal.status, "needs_evidence"),
        origin: dashboardText(goal.origin, "source_observation"),
        hypothesis: dashboardText(goal.hypothesis, "Research goal has no hypothesis exported."),
        market_channel: dashboardText(goal.market_channel, "macro_watchlist"),
        watched_instruments: asArray(goal.watched_instruments).slice(0, 6),
        required_sources: asArray(goal.required_sources).slice(0, 8),
        minimum_source_quorum: modelNumber(goal.minimum_source_quorum, 2),
        worldview_lens: dashboardText(goal.worldview_lens, "private_world_model_prior_only"),
        akber_stage: dashboardText(goal.akber_stage, "stage_1_catalyst_identification"),
        missing_corroboration: asArray(goal.missing_corroboration).slice(0, 8),
        owner_agent: dashboardText(goal.owner_agent, "research_analyst"),
        next_handoff: dashboardText(goal.next_handoff, "local_research_analyst_compression"),
        execution_allowed: false,
        paper_order_allowed: false,
        trade_candidate_creation_allowed: false,
        risk_handoff_allowed: false,
        broker_write_allowed: false,
        live_capital_enabled: false,
        updated_at: goal.updated_at,
        boundary: dashboardText(goal.boundary, "Research Goal is pre-signal research state.")
    }));
    const evidenceIndex = evidencePackets.slice(0, 5).map((packet) => ({
        trail_id: dashboardText(packet.trail_id, "evidence_packet"),
        signal_id: dashboardText(packet.signal_id, "unlinked_signal"),
        source_count: modelNumber(packet.source_count, 0),
        sources: asArray(packet.sources).slice(0, 6),
        item_count: asArray(packet.items).length,
        average_trust_score: packet.average_trust_score,
        min_trust_score: packet.min_trust_score,
        missing_corroboration: asArray(packet.missing_correlations).slice(0, 6),
        created_at: packet.created_at,
        items: asArray(packet.items).slice(0, 3).map((item) => ({
            source: dashboardText(item.source, "source"),
            event_type: dashboardText(item.event_type, "event"),
            summary: dashboardText(item.summary, "No summary."),
            trust_score: item.trust_score,
            evidence_role: "factual_evidence_item"
        })),
        boundary: "Evidence packet only. It can support review but cannot create a trade idea or order."
    }));
    const missingCorroboration = compactUnique([
        ...researchGoals.flatMap((goal) => asArray(goal.missing_corroboration)),
        ...hypotheses.flatMap((hypothesis) => asArray(hypothesis.missing_correlations)),
        ...evidencePackets.flatMap((packet) => asArray(packet.missing_correlations)),
        ...localResearch.flatMap((assessment) => asArray(assessment.missing_correlations)),
        ...strategyPackets.flatMap((packet) => asArray(packet.missing_correlations)),
        ...asArray(latestStrategyReview.required_challenges),
        ...signalReviews.flatMap((review) => asArray(review.required_next_steps))
    ], 10).map((item) => ({
        label: item,
        status: /risk|gate|approval|blocked/i.test(item) ? "blocked" : "pending",
        why_it_matters: "Qadam holds the idea until this missing corroboration is resolved.",
        boundary: "Missing corroboration is a normal blocker, not an error."
    }));
    const blockerRecords = compactUnique([
        ...asArray(cognition.blocked_reasons),
        ...hypotheses.map((hypothesis) => hypothesis.blocked_reason),
        ...signalReviews.flatMap((review) => asArray(review.failure_reasons))
    ], 12);
    const reviewChain = [
        {
            key: "research_analyst",
            label: "Research Analyst review",
            role: "Local LLM",
            status: dashboardText(latestAssessment.status, localResearch.length ? "shadow_only" : "not_exported"),
            summary: dashboardText(latestAssessment.summary, "No local assessment exported."),
            focus: dashboardText(latestAssessment.watch_focus, "no focus exported"),
            missing_corroboration: asArray(latestAssessment.missing_correlations).slice(0, 6),
            can_advance_trade: false,
            boundary: "Local review compresses the queue only. No paper/order authority."
        },
        {
            key: "strategy_lead",
            label: "Strategy Lead review",
            role: "Frontier LLM",
            status: dashboardText(latestStrategyPacket.status, strategyPackets.length ? "queued_shadow_only" : "not_exported"),
            summary: dashboardText(latestStrategyReview.boundary || latestStrategyPacket.boundary, "No Strategy Lead packet exported."),
            focus: dashboardText(latestStrategyPacket.watch_focus, "strategy handoff not exported"),
            missing_corroboration: asArray(latestStrategyReview.required_challenges).slice(0, 8),
            can_advance_trade: false,
            boundary: "Strategy Lead is challenge-only and cannot approve risk or create trade candidates."
        },
        {
            key: "signal_integrity",
            label: "Signal Integrity review",
            role: "Gate",
            status: dashboardText(latestSignalReview.status, signalIntegrity.status || "not_exported"),
            summary: dashboardText(latestSignalReview.boundary || signalIntegrity.boundary, "No Signal Integrity review exported."),
            focus: dashboardText(latestSignalReview.instrument_focus, "no reviewed instrument"),
            missing_corroboration: asArray(latestSignalReview.missing_correlations).slice(0, 6),
            can_advance_trade: false,
            boundary: "Signal Integrity can hold or block. It cannot write orders."
        },
        {
            key: "head_of_quant",
            label: "Head of Quant annotation",
            role: "Quantum/classical oracle",
            status: dashboardText(fireOpalIbm.status || quantum.latest_output_routing_status || quantum.status, "not_exported"),
            summary: dashboardText(fireOpalIbm.boundary || quantumRouting.boundary || quantum.boundary, "No oracle annotation exported."),
            focus: dashboardText(quantum.latest_recommendation || quantumRouting.recommendation, "hold"),
            missing_corroboration: compactUnique([
                fireOpalIbm.blocker && fireOpalIbm.blocker !== "none" ? `Fire Opal IBM: ${fireOpalIbm.blocker}` : null,
                ...Object.entries(quantum.latest_validation_checks || {}).map(([key, value]) => `${key}: ${value}`)
            ], 6),
            can_advance_trade: false,
            boundary: "Head of Quant output is a shadow annotation only."
        }
    ];
    const quantAnnotation = {
        status: dashboardText(quantum.latest_output_routing_status || quantum.status, "not exported"),
        backend: dashboardText(quantum.latest_backend || quantum.backend || quantum.quantum_oracle_backend, "classical fallback"),
        recommendation: dashboardText(quantum.latest_recommendation || quantumRouting.recommendation, "hold"),
        route_type: dashboardText(quantum.latest_output_route_type || quantumRouting.route_type, "shadow annotation"),
        annotation_target: dashboardText(quantum.latest_output_annotation_target || quantumRouting.annotation_target, "reviewed shadow context"),
        hardware_submitted_count: modelNumber(quantum.hardware_submitted_count, 0),
        fire_opal_ibm_status: dashboardText(fireOpalIbm.status, "not exported"),
        fire_opal_ibm_blocker: dashboardText(fireOpalIbm.blocker, "not exported"),
        fire_opal_access_verified: Boolean(fireOpalIbm.fire_opal_product_access_verified),
        qiskit_runtime_ready: Boolean(fireOpalIbm.qiskit_ibm_runtime_importable && fireOpalIbm.qiskit_importable),
        ibm_credentials_configured: Boolean(fireOpalIbm.ibm_quantum_token_configured && fireOpalIbm.ibm_quantum_instance_configured),
        hardware_submission_allowed: Boolean(fireOpalIbm.hardware_submission_allowed),
        trade_candidate_created_count: modelNumber(quantum.trade_candidate_created_count || quantumRouting.trade_candidate_created_count, 0),
        paper_order_allowed: Boolean(quantumRouting.paper_order_allowed),
        execution_allowed: Boolean(quantumRouting.execution_allowed),
        boundary: dashboardText(
            fireOpalIbm.boundary || quantumRouting.boundary || quantum.boundary,
            "Head of Quant output is a shadow annotation only."
        )
    };
    const laneRecords = [
        {
            key: "worldview_prior",
            label: "Worldview prior",
            status: philosophy.status === "ok" ? "prior_only" : "pending",
            summary: `${worldviewLenses.length} private priors shape questions before evidence.`,
            watch: "Prior, not evidence",
            boundary: dashboardText(philosophy.boundary, "Worldview claims are private priors, not factual evidence.")
        },
        {
            key: "factual_evidence",
            label: "Factual evidence",
            status: evidencePackets.length ? "online" : "pending",
            summary: `${evidencePackets.length} packets and ${sumNestedItems(evidencePackets, "items")} items support the review queue.`,
            watch: "Source count, trust, and missing corroboration",
            boundary: "Evidence supports review but cannot create orders."
        },
        {
            key: "hypothesis_queue",
            label: "Goals and hypotheses",
            status: researchGoals.length || hypotheses.length ? "pending" : "neutral",
            summary: `${researchGoals.length} research goals and ${hypotheses.length} hypotheses remain before candidate state.`,
            watch: "Pre-signal research, not trade idea",
            boundary: "Research Goals and hypotheses cannot be mistaken for trade ideas or orders."
        },
        {
            key: "missing_corroboration",
            label: "Missing corroboration",
            status: missingCorroboration.length ? "blocked" : "online",
            summary: `${missingCorroboration.length} blockers or challenge questions remain visible.`,
            watch: "Normal blocker",
            boundary: "A missing item holds the idea; it does not unlock authority."
        },
        {
            key: "strategy_review",
            label: "Strategy Lead review",
            status: strategyPackets.length ? "pending" : "neutral",
            summary: `${strategyPackets.length} Strategy Lead packets challenge the queue.`,
            watch: "Challenge-only",
            boundary: "Strategy Lead cannot approve risk or create trade candidates."
        },
        {
            key: "quant_annotation",
            label: "Quant/quantum annotation",
            status: quantAnnotation.status,
            summary: `${quantAnnotation.backend} recommends ${quantAnnotation.recommendation}.`,
            watch: "Shadow annotation",
            boundary: quantAnnotation.boundary
        }
    ];
    const reviewGroups = [
        {
            id: "prior_evidence_basis",
            label: "Prior and evidence basis",
            summary: "Private priors, factual evidence packets, and the reason each must stay separate.",
            record_count: worldviewLenses.length + evidenceIndex.length,
            tone: evidenceIndex.length ? "online" : "pending"
        },
        {
            id: "hypotheses_blockers",
            label: "Hypotheses and blockers",
            summary: "Research goals, current hypotheses, why they stalled, and missing corroboration that holds them.",
            record_count: researchGoalQueue.length + hypothesisQueue.length + missingCorroboration.length,
            tone: missingCorroboration.length ? "blocked" : "pending"
        },
        {
            id: "review_chain",
            label: "Review chain and quant annotation",
            summary: "Research Analyst, Strategy Lead, Signal Integrity, and Head of Quant annotations.",
            record_count: reviewChain.length + 1,
            tone: reviewChain.some((review) => /blocked|hold|pending/i.test(review.status)) ? "pending" : "online"
        }
    ];
    return {
        id: "reasoning",
        label: "Reasoning",
        question: "Why does Qadam care, and what is still missing?",
        tone: executableHypotheses.length ? "blocked" : (hypotheses.length ? "pending" : "neutral"),
        summary: `${researchGoals.length} research goals, ${hypotheses.length} hypotheses, ${evidencePackets.length} evidence packets, ${shadowPackets.length} research packets, ${executableHypotheses.length} executable hypotheses.`,
        counts: {
            research_goals: researchGoals.length,
            hypotheses: hypotheses.length,
            evidence_packets: evidencePackets.length,
            evidence_items: sumNestedItems(evidencePackets, "items"),
            shadow_packets: shadowPackets.length,
            local_research_assessments: localResearch.length,
            strategy_packets: strategyPackets.length,
            executable_hypotheses: executableHypotheses.length
        },
        lanes: laneRecords,
        reasoning_review_groups: reviewGroups,
        worldview_prior: {
            status: dashboardText(philosophy.status, "not_exported"),
            role: dashboardText(philosophy.role, "private_worldview_prior"),
            trading_philosophy: dashboardText(
                philosophy.trading_philosophy,
                "Qadam uses worldview context to ask better questions, not as evidence."
            ),
            decision_chain: asArray(philosophy.decision_chain),
            active_lenses: worldviewLenses,
            claim_count: modelNumber(philosophy.claim_count, worldviewLenses.length),
            evidence_role: "prior_not_evidence",
            is_evidence: false,
            boundary: dashboardText(philosophy.boundary, "Worldview claims are private priors, not evidence.")
        },
        research_goals: {
            status: dashboardText(researchGoalState.status, researchGoals.length ? "ok" : "not_exported"),
            active_goal_count: modelNumber(researchGoalState.active_goal_count, researchGoals.length),
            record_count: modelNumber(researchGoalState.goal_record_count, researchGoals.length),
            by_status: researchGoalState.by_status || {},
            by_market_channel: researchGoalState.by_market_channel || {},
            boundary: dashboardText(
                researchGoalState.boundary,
                "Research Goals are pre-signal research state and cannot create candidates or orders."
            )
        },
        research_goal_queue: researchGoalQueue,
        hypothesis_queue: hypothesisQueue,
        evidence_packets: evidenceIndex,
        missing_corroboration: missingCorroboration,
        blocker_records: blockerRecords,
        review_chain: reviewChain,
        quant_annotation: quantAnnotation,
        strategy_governance: {
            approval_state: phase4.approval_event_status || phase4.approval_event?.approval_state || "missing",
            strategy_document_status: phase4.strategy_document_status || "missing",
            certification_status: phase4.certification_status || "not run",
            toggle_count: modelNumber(phase4.toggle_count || phase4.strategy_toggles?.toggle_count, 0)
        },
        quant_review: {
            status: quantum.status || "not exported",
            backend: quantum.backend || quantum.quantum_oracle_backend || "classical fallback",
            hardware_submitted_count: modelNumber(quantum.hardware_submitted_count, 0),
            recommendation: quantum.latest_recommendation || quantum.recommendation || "hold"
        },
        empty_state: hypotheses.length ? null : dashboardModelEmptyState("missing", 0, {
            title: "No hypotheses visible",
            body: "Qadam has no hypotheses in this status snapshot yet.",
            tone: "neutral"
        }),
        boundary: `${cognition.boundary || "Reasoning is research-only until backend gates say otherwise."} Priors are not evidence, hypotheses are not trade ideas, and model output cannot create orders.`
    };
}

function buildPerformanceModel(status = {}) {
    const capital = status.capital || {};
    const phase7 = status.phase7_demo_proof || {};
    const paperLive = status.paper_live_certification || {};
    const closedProof = modelNumber(phase7.closed_proof_trade_count, 0);
    const proofTarget = modelNumber(phase7.mature_benchmark, 100);
    const startingValue = modelNumber(
        paperLive.paper_growth_trial_starting_value_gbp,
        modelNumber(capital.starting_balance_gbp, 100000)
    );
    const targetValue = modelNumber(
        paperLive.paper_growth_trial_target_value_gbp,
        startingValue * 2
    );
    const targetDays = modelNumber(paperLive.paper_growth_trial_horizon_days, 60);
    const currentValue = modelNumber(
        capital.equity_gbp ?? capital.current_balance_gbp,
        startingValue
    );
    const targetProgress = targetValue > startingValue
        ? Math.min(1, Math.max(0, (currentValue - startingValue) / (targetValue - startingValue)))
        : 0;
    const completedDays = modelNumber(phase7.completed_calendar_day_count, 0);
    const requiredDays = modelNumber(phase7.phase7_harness_day_count, 30);
    const proofWeeks = modelNumber(phase7.proof_week_count, 5);
    const currentWeek = modelNumber(phase7.current_proof_week_number, 0);
    const weeklyTarget = modelNumber(phase7.weekly_proof_trade_target, 3);
    const postmortemsDue = asArray(capital.postmortems_due);
    const operationalComplete = Boolean(phase7.phase7_30_day_run_complete) || completedDays >= requiredDays;
    const dayProgress = requiredDays ? Math.min(1, Math.max(0, completedDays / requiredDays)) : 0;
    const maturityProgress = proofTarget ? Math.min(1, Math.max(0, closedProof / proofTarget)) : 0;
    const drawdownWithinCap = phase7.drawdown_within_cap !== false && !phase7.drawdown_cap_breached;
    const riskHaltActive = Boolean(phase7.risk_halt_active || phase7.drawdown_cap_breached || capital.live_capital_enabled);
    const forcedTradePressure =
        Boolean(phase7.phase7_proof_credit_allowed)
        || Boolean(phase7.phase5_test_trades_count_for_phase7)
        || Boolean(phase7.phase7_statistical_immaturity_hidden)
        || Boolean(phase7.new_proof_trades_frozen && !phase7.risk_halt_active);
    const proofCreditSafe = Boolean(phase7.phase7_proof_credit_allowed) && closedProof >= proofTarget && completedDays >= requiredDays;
    const closedPaperTrades = asArray(capital.closed_trades);
    const openPositions = asArray(capital.open_positions);
    const orders = asArray(capital.orders);
    const totalPnl = modelNumber(capital.realized_pnl_gbp, 0) + modelNumber(capital.unrealized_pnl_gbp, 0);
    const tone = capital.live_capital_enabled || riskHaltActive || postmortemsDue.length || forcedTradePressure
        ? "blocked"
        : (closedProof || completedDays ? "pending" : "online");
    const sourceRecords = asArray(phase7.source_status_records).slice(0, 14).map((record) => ({
        key: dashboardText(record.source_key, "phase7_source"),
        stage: dashboardText(record.source_stage, "Q7"),
        status: dashboardText(record.display_status || record.source_status || record.backend_status, "not exported"),
        backend_status: dashboardText(record.backend_status, "not exported"),
        source_ref: dashboardText(record.source_ref, "not exported"),
        event_log_written: Boolean(record.event_log_written),
        ui_inferred_readiness: Boolean(record.ui_inferred_readiness),
        public_safe: record.public_safe !== false
    }));
    return {
        id: "performance",
        label: "Performance",
        question: "Is the paper account growing toward target?",
        tone,
        summary: `${formatMoney(currentValue)} toward ${formatMoney(targetValue)} over ${targetDays} days; ${formatMoney(totalPnl)} paper P&L, drawdown ${drawdownWithinCap ? "within cap" : "breached"}.`,
        growth_trial: {
            name: dashboardText(paperLive.paper_growth_trial_name, "60-day paper growth trial"),
            starting_value_gbp: startingValue,
            target_value_gbp: targetValue,
            target_multiple: modelNumber(paperLive.paper_growth_trial_target_multiple, 2),
            horizon_days: targetDays,
            current_value_gbp: currentValue,
            progress_fraction: targetProgress,
            mindset: dashboardText(
                paperLive.paper_growth_trial_mindset,
                "Selective larger paper moves when evidence, strategy, Q-CTRL, risk, and Alpaca Paper gates agree."
            ),
            operation_allowed: Boolean(paperLive.paper_live_operation_allowed),
            certified: Boolean(paperLive.paper_live_certified),
            unattended_execution_delegation_enabled: Boolean(
                paperLive.paper_live_unattended_execution_delegation_enabled
            ),
            unattended_execution_delegation_reason: dashboardText(
                paperLive.paper_live_unattended_execution_delegation_reason,
                "not armed"
            ),
            submission_delegation_allowed: Boolean(
                paperLive.paper_live_submission_delegation_allowed
            )
        },
        paper_account: {
            starting_balance_gbp: modelNumber(capital.starting_balance_gbp, 0),
            current_balance_gbp: modelNumber(capital.current_balance_gbp, 0),
            cash_gbp: modelNumber(capital.cash_gbp, 0),
            equity_gbp: modelNumber(capital.equity_gbp, 0),
            realized_pnl_gbp: modelNumber(capital.realized_pnl_gbp, 0),
            unrealized_pnl_gbp: modelNumber(capital.unrealized_pnl_gbp, 0),
            total_pnl_gbp: totalPnl,
            drawdown_pct: modelNumber(capital.drawdown_pct, 0),
            max_drawdown_pct: modelNumber(capital.max_drawdown_pct, 0),
            open_position_count: openPositions.length,
            order_count: orders.length,
            closed_paper_trade_count: closedPaperTrades.length,
            postmortem_due_count: postmortemsDue.length,
            postmortem_complete_count: modelNumber(capital.postmortem_complete_count, asArray(capital.postmortems_complete).length),
            timeline_status: dashboardText(capital.timeline_status, "not exported"),
            connection_status: dashboardText(capital.connection_status, "not exported"),
            write_authority: Boolean(capital.write_authority),
            live_capital_enabled: Boolean(capital.live_capital_enabled)
        },
        demo_proof: {
            status: dashboardText(phase7.status, "not exported"),
            proof_state: dashboardText(phase7.proof_state, "not exported"),
            completed_calendar_day_count: completedDays,
            required_calendar_day_count: requiredDays,
            day_progress_fraction: dayProgress,
            phase7_30_day_run_complete: operationalComplete,
            current_proof_week_number: currentWeek,
            proof_week_count: proofWeeks,
            weekly_proof_trade_target: weeklyTarget,
            weekly_target_formula: dashboardText(phase7.weekly_target_formula, "min(3, qualified_setup_count)"),
            qualified_setup_count: modelNumber(phase7.qualified_setup_count, 0),
            eligible_setup_count: modelNumber(phase7.eligible_setup_count, 0),
            candidate_setup_count: modelNumber(phase7.candidate_setup_count, 0),
            missed_qualified_setup_count: modelNumber(phase7.missed_qualified_setup_count, 0),
            missed_qualified_setup_unexplained_count: modelNumber(phase7.missed_qualified_setup_unexplained_count, 0),
            staged_proof_order_count: modelNumber(phase7.staged_proof_order_count, 0),
            submitted_paper_order_count: modelNumber(phase7.submitted_paper_order_count, 0),
            broker_receipt_count: modelNumber(phase7.broker_receipt_count, 0),
            mirrored_submitted_order_count: modelNumber(phase7.mirrored_submitted_order_count, 0),
            open_position_count: modelNumber(phase7.open_position_count, 0),
            closed_proof_trade_count: closedProof,
            postmortem_due_count: modelNumber(phase7.postmortem_due_count, 0),
            postmortem_reviewed_count: modelNumber(phase7.postmortem_reviewed_count, 0),
            proof_trade_credit_count: modelNumber(phase7.proof_trade_credit_count, 0),
            mature_benchmark: proofTarget,
            maturity_progress_fraction: maturityProgress,
            backend_reported_proof_credit_allowed: Boolean(phase7.phase7_proof_credit_allowed),
            display_proof_credit_allowed: proofCreditSafe,
            phase5_test_trades_count_for_phase7: Boolean(phase7.phase5_test_trades_count_for_phase7),
            backend_derived: Boolean(phase7.backend_derived),
            display_derived_from_backend: Boolean(phase7.display_derived_from_backend),
            ui_inferred_readiness_count: modelNumber(phase7.ui_inferred_readiness_count, 0),
            q7_16_weekly_review_pack_stage_allowed: Boolean(phase7.q7_16_weekly_review_pack_stage_allowed)
        },
        risk_state: {
            drawdown_state: dashboardText(phase7.drawdown_state, "not exported"),
            drawdown_within_cap: drawdownWithinCap,
            drawdown_cap_breached: Boolean(phase7.drawdown_cap_breached),
            max_drawdown_fraction_observed: modelNumber(phase7.max_drawdown_fraction_observed, 0),
            risk_halt_active: riskHaltActive,
            override_count: modelNumber(phase7.override_count, 0),
            sample_contaminated: Boolean(phase7.sample_contaminated),
            new_proof_trades_frozen: Boolean(phase7.new_proof_trades_frozen),
            live_capital_enabled: Boolean(phase7.live_capital_enabled || capital.live_capital_enabled)
        },
        operational_vs_maturity: {
            operational_run_complete: operationalComplete,
            operational_run_progress_fraction: dayProgress,
            maturity_state: dashboardText(phase7.maturity_state, "not exported"),
            maturity_benchmark: proofTarget,
            closed_proof_trade_count: closedProof,
            closed_trades_remaining_to_mature: modelNumber(phase7.closed_trades_remaining_to_mature, Math.max(0, proofTarget - closedProof)),
            phase7_mature_benchmark_met: Boolean(phase7.phase7_mature_benchmark_met),
            phase7_mature_status_blocked: Boolean(phase7.phase7_mature_status_blocked),
            phase7_statistical_immaturity_hidden: Boolean(phase7.phase7_statistical_immaturity_hidden),
            phase7_certification_blocked_by_maturity: Boolean(phase7.phase7_certification_blocked_by_maturity),
            operational_completion_erased_by_immaturity: Boolean(phase7.phase7_30_day_operational_result_erased_by_immaturity),
            boundary: "The 60-day growth target and verified performance maturity are separate. The UI must not force trades to reach the target."
        },
        proof_quality: {
            complete_decision_chain_count: modelNumber(phase7.complete_decision_chain_count, 0),
            missing_decision_chain_count: modelNumber(phase7.missing_decision_chain_count, 0),
            event_log_written: Boolean(phase7.event_log_written),
            source_artifact_count: modelNumber(phase7.source_artifact_count, sourceRecords.length),
            source_missing_count: modelNumber(phase7.source_missing_count, 0),
            source_validation_error_count: modelNumber(phase7.source_validation_error_count, 0),
            source_status_records: sourceRecords
        },
        safety_boundary: {
            forced_trade_pressure_detected: forcedTradePressure,
            broker_post_called_count: modelNumber(phase7.broker_post_called_count, 0),
            alpaca_post_called_count: modelNumber(phase7.alpaca_post_called_count, 0),
            unsafe_write_counter_total: modelNumber(phase7.unsafe_write_counter_total, 0),
            prediction_market_write_allowed_count: modelNumber(phase7.prediction_market_write_allowed_count, 0),
            crypto_perps_write_allowed_count: modelNumber(phase7.crypto_perps_write_allowed_count, 0),
            live_capital_enabled_count: modelNumber(phase7.live_capital_enabled_count, 0),
            blocker_count: modelNumber(phase7.blocker_count, 0),
            blockers: asArray(phase7.blockers)
        },
        empty_state: asArray(capital.closed_trades).length ? null : dashboardModelEmptyState("normal_no_trade"),
        boundary: `${capital.boundary || "Read-only paper account mirror. No funding authority and no live broker-write authority."} Paper-trading performance is backend-derived; this view cannot force trades, infer performance credit, write brokers, or enable live capital.`
    };
}

function sourcePipelineStatus(pipeline = {}) {
    if (modelNumber(pipeline.missing_credential_count, 0) || modelNumber(pipeline.degraded_count, 0)) return "degraded";
    if (modelNumber(pipeline.online_count, 0) || modelNumber(pipeline.adapter_ready_count, 0)) return "online";
    return "pending";
}

function buildOperationsFeedClusters(status = {}, sourcePosture = {}) {
    const watching = asArray(status.watching);
    const byPipeline = watching.reduce((acc, source) => {
        const key = source.pipeline || "unknown";
        acc[key] = acc[key] || [];
        acc[key].push(source);
        return acc;
    }, {});
    const pipelineSummary = asArray(status.source_pipeline_summary);
    const pipelineClusters = pipelineSummary.map((pipeline) => {
        const key = pipeline.pipeline || "unknown";
        const sources = asArray(byPipeline[key]);
        return {
            key,
            label: OPERATIONS_PIPELINE_LABELS[key] || dashboardText(key),
            status: sourcePipelineStatus(pipeline),
            authority: "observation only",
            source_count: modelNumber(pipeline.source_count, sources.length),
            count: modelNumber(pipeline.source_count, sources.length),
            online_count: modelNumber(pipeline.online_count, 0),
            degraded_count: modelNumber(pipeline.degraded_count, 0),
            pending_count: modelNumber(pipeline.pending_count, 0),
            missing_credential_count: modelNumber(pipeline.missing_credential_count, 0),
            adapter_ready_count: modelNumber(pipeline.adapter_ready_count, 0),
            provenance: "source registry and sanitized dashboard status",
            sources: sources
                .slice()
                .sort((a, b) => String(a.source_name || a.source_key).localeCompare(String(b.source_name || b.source_key)))
                .slice(0, 8)
                .map((source) => ({
                    key: source.source_key,
                    label: source.source_name || source.source_key,
                    status: source.status || "pending",
                    readiness: source.readiness || source.registry_status || "not exported",
                    credential_status: source.credential_status || "not exported",
                    promoted_adapter: Boolean(source.promoted_adapter),
                    heartbeat: source.last_heartbeat
                }))
        };
    });
    const canonical = sourcePosture.canonical || status.durable_ingestion || {};
    const supplementalClusters = [
        {
            key: "canonical_replay",
            label: "Canonical replay provenance",
            status: canonical.status || status.durable_ingestion?.status || "not exported",
            authority: "canonical replay required",
            source_count: modelNumber(canonical.replayed_source_count, modelNumber(status.durable_ingestion?.replayed_source_count, 0)),
            count: modelNumber(canonical.replayed_source_count, modelNumber(status.durable_ingestion?.replayed_source_count, 0)),
            online_count: modelNumber(canonical.replayed_source_count, 0),
            degraded_count: modelNumber(canonical.missing_source_count, 0),
            pending_count: Math.max(0, modelNumber(canonical.expected_source_count, 0) - modelNumber(canonical.replayed_source_count, 0)),
            missing_credential_count: 0,
            adapter_ready_count: modelNumber(canonical.replayed_source_count, 0),
            provenance: "durable replay source-of-truth coverage",
            sources: []
        },
        {
            key: "supplemental_market_confirmation",
            label: "Supplemental market confirmation",
            status: status.yahoo_finance?.status || sourcePosture.yahoo_finance?.status || "not exported",
            authority: "supplemental confirmation only",
            source_count: modelNumber(status.yahoo_finance?.symbol_allowlist_count, 0),
            count: modelNumber(status.yahoo_finance?.symbol_allowlist_count, 0),
            online_count: status.yahoo_finance?.enabled ? 1 : 0,
            degraded_count: status.yahoo_finance?.degraded ? 1 : 0,
            pending_count: status.yahoo_finance?.enabled ? 0 : 1,
            missing_credential_count: 0,
            adapter_ready_count: status.yahoo_finance?.sample_mode_available ? 1 : 0,
            provenance: "Yahoo Finance sample/live-read adapter status",
            sources: []
        },
        {
            key: "supplemental_world_context",
            label: "Supplemental world and prediction context",
            status: status.preference_mcp?.status || sourcePosture.preference_mcp?.status || "not exported",
            authority: "challenge-only context",
            source_count: modelNumber(status.preference_mcp?.approved_domain_pack_count, 0),
            count: modelNumber(status.preference_mcp?.approved_domain_pack_count, 0),
            online_count: status.preference_mcp?.enabled ? 1 : 0,
            degraded_count: status.preference_mcp?.degraded ? 1 : 0,
            pending_count: status.preference_mcp?.enabled ? 0 : 1,
            missing_credential_count: status.preference_mcp?.identity_status === "verified" ? 0 : 1,
            adapter_ready_count: status.preference_mcp?.provenance_status === "validated" ? 1 : 0,
            provenance: "Preference MCP domain-pack and provenance gate",
            sources: []
        }
    ];
    return [...pipelineClusters, ...supplementalClusters];
}

function relatedDashboardLinksForNode(key) {
    const links = {
        watching: ["#evidence", "#overview"],
        yahoo_finance: ["#evidence"],
        preference_mcp: ["#evidence"],
        event_log: ["#operations"],
        live_bridge: ["#operations"],
        worldview: ["#reasoning"],
        research_analyst: ["#reasoning"],
        strategy_lead: ["#reasoning"],
        head_of_quant: ["#operations", "#reasoning"],
        shadow_intelligence: ["#reasoning"],
        signal_integrity_gate: ["#reasoning", "#trades"],
        approval_policy_router: ["#trades", "#operations"],
        risk_agent: ["#trades", "#operations"],
        kill_switch_ledger: ["#operations"],
        execution_adapter_status: ["#operations", "#trades"],
        execution_policy: ["#trades", "#operations"],
        staged_order_contract: ["#trades", "#operations"],
        broker_reconciliation: ["#trades", "#operations"],
        paper_submit_receipt: ["#trades", "#operations"],
        prediction_market_adapter: ["#evidence", "#trades"],
        trade_layer: ["#trades"],
        paper_account: ["#trades"],
        position_monitor: ["#trades"],
        postmortem_loop: ["#trades", "#operations"],
        telegram_notifier: ["#operations"],
        signal_review: ["#trades", "#operations"],
        fund_manager_forum: ["#operations"]
    };
    return links[key] || ["#operations"];
}

function operationsEdgeStateForLane(lane = {}) {
    const text = `${lane.key || ""} ${lane.title || ""} ${lane.tone || ""}`.toLowerCase();
    if (text.includes("blocked") || text.includes("risk") || text.includes("gate")) return "blocked";
    if (text.includes("degraded")) return "degraded";
    if (text.includes("research") || text.includes("strategy") || text.includes("shadow")) return "shadow/context-only";
    if (text.includes("paper") || text.includes("execution")) return "locked";
    return "active";
}

function buildOperationsRoleSpine(connectivity) {
    const nodesByKey = new Map(asArray(connectivity.nodes).map((node) => [node.key, node]));
    return OPERATIONS_ROLE_SPINE.map((role) => {
        const nodes = asArray(role.node_keys).map((key) => nodesByKey.get(key)).filter(Boolean);
        const hasBlocked = nodes.some((node) => node.health === "blocked" || node.authority_flags?.length);
        const hasDegraded = nodes.some((node) => node.health === "degraded");
        const hasPending = nodes.some((node) => node.health === "pending");
        return {
            ...role,
            status: hasBlocked ? "blocked" : (hasDegraded ? "degraded" : (hasPending ? "pending" : "online")),
            node_count: nodes.length,
            nodes: nodes.map((node) => node.key)
        };
    });
}

function buildSystemConnectivityModel(status = {}) {
    const backendMap = status.phase5_system_map || {};
    const backendNodes = asArray(backendMap.nodes);
    const nodes = backendNodes.length ? backendNodes : asArray(status.modules);
    const nodeModels = nodes.map((node, index) => {
        const details = flowNodeDetails(node);
        const authority = systemMapAuthorityLabel(node, details);
        const displayStatus = node.display_status || node.status || node.backend_status || "pending";
        const authorityFlags = [
            ["trade_approval", node.trade_approval_control_enabled],
            ["order_place", node.order_place_control_enabled],
            ["broker_write", node.broker_write_allowed],
            ["live_capital", node.live_capital_enabled],
            ["prediction_market_write", node.prediction_market_write_allowed],
            ["kill_switch_mutation", node.kill_switch_mutation_authority]
        ].filter(([, value]) => Boolean(value)).map(([key]) => key);
        return {
            id: node.key || `node_${index + 1}`,
            key: node.key || `node_${index + 1}`,
            label: dashboardText(node.label, node.key || "System node"),
            lane: dashboardText(node.lane, "Operations"),
            role: dashboardText(details.role, node.owner || "Qadam desk"),
            status: dashboardText(displayStatus, "pending"),
            health: normalizeModelHealth(displayStatus, authority),
            input: dashboardText(details.input, "Runtime state"),
            output: dashboardText(details.output, "Dashboard state"),
            purpose: dashboardText(node.purpose || node.current_process || details.role, "System node diagnostic"),
            authority,
            authority_flags: authorityFlags,
            public_safe: node.public_safe !== false,
            ui_inferred: Boolean(node.ui_inferred),
            counts: node.counts || {},
            blockers: asArray(node.blockers),
            expanded: {
                purpose: dashboardText(node.purpose || node.current_process || details.role, "System node diagnostic"),
                current_process: dashboardText(node.current_process, "No current process exported"),
                current_status: dashboardText(displayStatus, "pending"),
                latest_heartbeat: dashboardText(node.latest_heartbeat || node.last_heartbeat || node.generated_at || status.generated_at, "not exported"),
                dependencies: asArray(node.dependencies).length ? asArray(node.dependencies) : [dashboardText(node.lane, "Operations lane")],
                degraded_reasons: asArray(node.blockers).length
                    ? asArray(node.blockers)
                    : (normalizeModelHealth(displayStatus, authority) === "degraded" || normalizeModelHealth(displayStatus, authority) === "blocked"
                        ? [dashboardText(displayStatus, "not exported")]
                        : []),
                backend_status_path: dashboardText(node.backend_status_path, "not exported"),
                event_log_references: compactUnique([
                    node.backend_status_path,
                    node.artifact_id,
                    node.stage,
                    node.event_log_written ? "event log written" : null
                ]),
                handoff: dashboardText(node.handoff, "passes state"),
                related_dashboard_links: relatedDashboardLinksForNode(node.key)
            }
        };
    });
    const nodeByKey = new Map(nodeModels.map((node) => [node.key, node]));
    const lanes = asArray(backendMap.lanes).length
        ? asArray(backendMap.lanes).map((lane) => ({
            key: lane.key,
            title: dashboardText(lane.title, lane.key || "System lane"),
            summary: dashboardText(lane.summary, "No lane summary exported"),
            tone: normalizeModelHealth(lane.tone),
            node_keys: asArray(lane.node_keys).filter((key) => nodeByKey.has(key)),
            handoff: dashboardText(lane.handoff, "passes state")
        }))
        : [{
            key: "operations",
            title: "Operations",
            summary: "Current dashboard modules.",
            tone: "pending",
            node_keys: nodeModels.map((node) => node.key),
            handoff: "state becomes dashboard readout"
        }];
    const edges = lanes.flatMap((lane) => lane.node_keys.slice(0, -1).map((from, index) => ({
        from,
        to: lane.node_keys[index + 1],
        lane: lane.key,
        state: operationsEdgeStateForLane(lane),
        label: lane.handoff,
        authority_boundary: "read-only status edge"
    })));
    const sourcePosture = backendMap.source_posture || {};
    const feedClusters = buildOperationsFeedClusters(status, sourcePosture);
    const authorityViolations = nodeModels
        .filter((node) => node.authority_flags.length || node.public_safe === false || node.ui_inferred)
        .map((node) => node.key);
    return {
        id: "system_connectivity_model",
        source: backendNodes.length ? "phase5_system_map" : "modules_fallback",
        node_count: nodeModels.length,
        lane_count: lanes.length,
        nodes: nodeModels,
        lanes,
        edges,
        feed_clusters: feedClusters,
        authority_violations: authorityViolations,
        overview_scope: {
            placement: "overview-mini-map",
            max_nodes: 8,
            node_keys: ["watching", "event_log", "research_analyst", "strategy_lead", "head_of_quant", "risk_agent", "trade_layer", "postmortem_loop"].filter((key) => nodeByKey.has(key))
        },
        operations_scope: {
            placement: "operations-full-map",
            node_keys: nodeModels.map((node) => node.key),
            role_keys: OPERATIONS_ROLE_SPINE.map((role) => role.key),
            edge_states: ["active", "shadow/context-only", "degraded", "locked", "blocked"]
        },
        boundary: backendMap.boundary || "The system map is read-only and sanitized for the dashboard."
    };
}

function buildOperationsModel(status = {}, source = {}, sharedModels = {}) {
    const liveBridge = status.live_bridge || {};
    const d1Snapshot = status.d1_snapshot || {};
    const d0Shell = status.d0_shell || {};
    const processEvents = asArray(status.process_console);
    const forbiddenActions = asArray(status.forbidden_actions);
    const connectivity = sharedModels.system_connectivity_model || buildSystemConnectivityModel(status);
    const roleSpine = buildOperationsRoleSpine(connectivity);
    const governance = sharedModels.governance_model || buildGovernanceModel(status);
    const communicationsAudit = governance.communications || {};
    const authorityFlags = collectAuthorityFlags(status);
    const readinessWarnings = collectReadinessWarnings(status);
    const moduleCounts = countBy(asArray(status.modules), "status");
    const pipelineSummary = asArray(status.source_pipeline_summary);
    const phase4 = phase4StrategyStatus(status);
    const phase7 = status.phase7_demo_proof || {};
    const killSwitch = status.phase5_kill_switch_ledger || status.phase5_kill_switch || {};
    const bridgeCache = liveBridge.cache_policy || {};
    const publisher = liveBridge.publisher || {};
    const brokenItems = [
        ...authorityFlags.map((flag) => `authority flag: ${flag}`),
        ...readinessWarnings.map((warning) => `readiness warning: ${warning}`),
        ...connectivity.authority_violations.map((key) => `map authority violation: ${key}`),
        ...pipelineSummary
            .filter((pipeline) => modelNumber(pipeline.missing_credential_count, 0) || modelNumber(pipeline.degraded_count, 0))
            .map((pipeline) => `${dashboardText(pipeline.pipeline)} pipeline degraded or missing credentials`),
        ...(processEvents.length ? [] : ["process console has no recent events"])
    ];
    const reviewGroups = [
        {
            id: "runtime_safety",
            title: "Runtime, bridge, and safety",
            summary: "Read-only bridge state, static fallback, exporter/cache posture, hard blocks, and kill-switch ledger.",
            status: brokenItems.length ? "degraded" : "online",
            count: 5 + forbiddenActions.length + brokenItems.length
        },
        {
            id: "team_data_plumbing",
            title: "Operating team and data plumbing",
            summary: "The hedge-fund team roles and intelligence feed clusters that move observations into review.",
            status: connectivity.feed_clusters.some((cluster) => cluster.status === "blocked") ? "blocked" : "online",
            count: roleSpine.length + connectivity.feed_clusters.length
        },
        {
            id: "system_map_event_trail",
            title: "Full system map and event trail",
            summary: "Node-by-node connectivity, handoff edge states, recent runtime events, and closed-loop logging rule.",
            status: connectivity.authority_violations.length ? "blocked" : "online",
            count: connectivity.node_count + processEvents.length
        },
        {
            id: "governance_comms_audit",
            title: "Governance and communications audit",
            summary: "Fund Manager comments, approval records, weekly review state, and outbound-only Telegram notifications.",
            status: communicationsAudit.command_path_enabled || communicationsAudit.live_send_allowed_count ? "blocked" : "pending",
            count: modelNumber(governance.comments?.count, 0) + modelNumber(communicationsAudit.pending_queue_count, 0) + asArray(governance.open_actions).length
        }
    ];
    return {
        id: "operations",
        label: "Operations",
        question: "Is the runtime, bridge, exporter, system map, and safety plumbing healthy?",
        tone: authorityFlags.length || connectivity.authority_violations.length ? "blocked" : (readinessWarnings.length ? "degraded" : "online"),
        summary: `${connectivity.node_count} system nodes; ${processEvents.length} process events; ${forbiddenActions.length} hard blocks; ${authorityFlags.length} authority flags.`,
        runtime: {
            status_source: source?.key || "unknown",
            generated_at: status.generated_at || null,
            schema_version: status.schema_version || null,
            live_bridge_status: liveBridge.status || "not exported",
            live_bridge_read_only: liveBridge.read_only !== false,
            allowed_methods: asArray(liveBridge.allowed_methods),
            forbidden_methods: asArray(liveBridge.forbidden_methods),
            endpoint: liveBridge.endpoint || "/api/cockpit-status",
            static_fallback: liveBridge.static_fallback || "/status/cockpit-status.json",
            d0_shell_status: d0Shell.status || "not exported",
            d1_snapshot_status: d1Snapshot.status || "not exported",
            public_safe: d1Snapshot.public_safe !== false,
            cache_mode: bridgeCache.mode || "not exported",
            cache_max_age_seconds: modelNumber(bridgeCache.max_age_seconds, 0),
            stale_after_seconds: modelNumber(bridgeCache.stale_after_seconds, 0),
            publisher_status: publisher.status || "not exported",
            signature_algorithm: publisher.signature_algorithm || "not exported",
            signature_configured: Boolean(publisher.signature_configured)
        },
        safety: {
            forbidden_action_count: forbiddenActions.length,
            authority_flags: authorityFlags,
            readiness_warnings: readinessWarnings,
            live_capital_enabled: Boolean(status.capital?.live_capital_enabled)
        },
        system_connectivity_model: connectivity,
        role_spine: roleSpine,
        operations_review_groups: reviewGroups,
        model_dependencies: {
            system_connectivity_model: connectivity.id || "system_connectivity_model",
            governance_model: governance.id || "governance"
        },
        forbidden_actions: forbiddenActions.slice(0, 8).map((action) => ({
            key: dashboardText(action.key, "safety stop"),
            reason: dashboardText(action.reason, "No reason exported.")
        })),
        process_events: processEvents.slice(-6).map((event) => ({
            timestamp: event.timestamp || event.created_at || event.generated_at,
            message: dashboardText(event.message || event.event || event.status, "runtime event")
        })),
        communications_audit: {
            status: communicationsAudit.telegram_status || "not exported",
            pending_queue_count: modelNumber(communicationsAudit.pending_queue_count, 0),
            dry_run_message_count: modelNumber(communicationsAudit.dry_run_message_count, 0),
            failed_count: modelNumber(communicationsAudit.failed_count, 0),
            suppressed_count: modelNumber(communicationsAudit.suppressed_count, 0),
            live_send_allowed_count: modelNumber(communicationsAudit.live_send_allowed_count, 0),
            command_path_enabled_count: modelNumber(communicationsAudit.command_path_enabled_count, 0),
            command_path_enabled: Boolean(communicationsAudit.command_path_enabled),
            send_gate: communicationsAudit.send_gate || "not exported",
            boundary: communicationsAudit.boundary || "Telegram is outbound notify-only."
        },
        governance_audit: {
            comments: modelNumber(governance.comments?.count, 0),
            suggestions: modelNumber(governance.comments?.suggestion_count, 0),
            accepted: modelNumber(governance.comments?.accepted_count, 0),
            implemented: modelNumber(governance.comments?.implemented_count, 0),
            approval: governance.approvals?.strategy_approval_state || "missing",
            weekly_review: governance.review_packs?.weekly_review_pack_state || "not ready",
            open_actions: asArray(governance.open_actions).slice(0, 4),
            live_promotion: governance.live_promotion?.status || "not eligible",
            boundary: governance.boundary || "Governance notes only. No trade approval, order placement, or local secret access."
        },
        broken_summary: {
            status: brokenItems.length ? "degraded" : "online",
            item_count: brokenItems.length,
            items: brokenItems.slice(0, 8),
            authority_flag_count: authorityFlags.length,
            readiness_warning_count: readinessWarnings.length,
            degraded_pipeline_count: pipelineSummary.filter((pipeline) => modelNumber(pipeline.missing_credential_count, 0) || modelNumber(pipeline.degraded_count, 0)).length,
            map_authority_violation_count: connectivity.authority_violations.length
        },
        diagnostics: {
            module_health: {
                total: asArray(status.modules).length,
                online: modelNumber(moduleCounts.online || moduleCounts.ok || moduleCounts.ready || moduleCounts.read_only_ready, 0),
                degraded: modelNumber(moduleCounts.degraded, 0),
                blocked: modelNumber(moduleCounts.blocked, 0),
                pending: modelNumber(moduleCounts.pending, 0),
                local_only: modelNumber(moduleCounts.local_only || moduleCounts["local-only"], 0)
            },
            exporter_state: {
                status_source: source?.key || "unknown",
                generated_at: status.generated_at || null,
                runtime_copy: d1Snapshot.runtime_copy || "not exported",
                landing_copy: d1Snapshot.landing_copy || "not exported",
                cache_mode: bridgeCache.mode || "not exported",
                static_fallback: liveBridge.static_fallback || "/status/cockpit-status.json",
                signature_status: publisher.status || "not exported",
                signature_configured: Boolean(publisher.signature_configured)
            },
            phase_certification: {
                phase4_stage: phase4.stage || "not exported",
                phase4_certified: Boolean(phase4.phase4_certified),
                phase5_certified: Boolean(status.phase5_certification?.phase5_certified),
                phase6_certified: Boolean(status.phase6_certification?.phase6_certified),
                phase7_visibility: phase7.stage_status || phase7.status || "not exported",
                phase7_certified: Boolean(status.phase7_certification?.phase7_certified)
            },
            kill_switch: {
                status: killSwitch.status || "not exported",
                total_count: modelNumber(killSwitch.kill_switch_count, 0),
                active_count: modelNumber(killSwitch.active_kill_switch_count || killSwitch.active_count, 0),
                blocking_count: modelNumber(killSwitch.blocking_kill_switch_count || killSwitch.blocking_count, 0),
                event_log_written: Boolean(killSwitch.event_log_written)
            }
        },
        latest_event: latestItem(processEvents),
        empty_state: processEvents.length ? null : dashboardModelEmptyState("missing"),
        boundary: "Operations is read-only diagnostics. It is not shell access and cannot run commands."
    };
}

function buildGovernanceCommentTargets(status = {}) {
    const candidates = asArray(status.trade_layer?.candidates);
    const observedSignals = asArray(status.trade_layer?.watching);
    const phase7 = status.phase7_demo_proof || {};
    const firstCandidate = candidates[0] || {};
    const firstSignal = observedSignals[0] || {};
    return [
        {
            view: "Trades",
            target_type: firstCandidate.instrument ? "trade_candidate" : "module",
            target_key: firstCandidate.instrument || "trade_layer",
            label: firstCandidate.instrument ? `Trade candidate: ${firstCandidate.instrument}` : "Trade lifecycle board",
            helper: "Comment on candidate quality, risk checks, blocked reasons, staged paper state, or postmortem needs.",
            href: "#trades"
        },
        {
            view: "Evidence",
            target_type: firstSignal.source ? "signal" : "source",
            target_key: firstSignal.signal_id || firstSignal.source || "source_health",
            label: firstSignal.instrument ? `Observed signal: ${firstSignal.instrument}` : "Source health and provenance",
            helper: "Comment on source coverage, stale data, missing credentials, or provenance quality.",
            href: "#evidence"
        },
        {
            view: "Reasoning",
            target_type: "strategy",
            target_key: "strategy_lead",
            label: "Strategy Lead / reasoning chain",
            helper: "Comment on hypotheses, worldview priors, missing corroboration, or challenge quality.",
            href: "#reasoning"
        },
        {
            view: "Trades",
            target_type: phase7.postmortem_due_count ? "postmortem" : "system",
            target_key: phase7.postmortem_due_count ? "postmortem_due" : "phase7_demo_proof",
            label: phase7.postmortem_due_count ? "Postmortem due" : "60-day paper growth trial",
            helper: "Comment on paper growth, drawdown, maturity, postmortems, or paper-account interpretation.",
            href: "#trades"
        },
        {
            view: "Operations",
            target_type: "system",
            target_key: "operations_health",
            label: "Operations health",
            helper: "Comment on bridge, exporter, system map, module health, source clusters, or safety rails.",
            href: "#operations"
        },
        {
            view: "Operations",
            target_type: "strategy",
            target_key: "phase4_strategy_approval",
            label: "Approval and review records",
            helper: "Comment on approvals, weekly review packs, Telegram state, or live-promotion readiness.",
            href: "#operations"
        }
    ];
}

function governanceRecord(label, state, detail, tone = "pending", extras = {}) {
    return {
        label,
        state: dashboardText(state, "not exported"),
        detail: dashboardText(detail, "No detail exported."),
        tone,
        event_log_written: Boolean(extras.event_log_written),
        boundary: dashboardText(extras.boundary, "Audit record only. No authority is granted by display."),
        href: extras.href || "#operations"
    };
}

function buildGovernanceApprovalRecords(status = {}) {
    const phase4 = phase4StrategyStatus(status);
    const phase5Certification = status.phase5_certification || {};
    const phase6 = status.phase6_learning_loop || {};
    const phase6Certification = status.phase6_certification || {};
    const phase7 = status.phase7_demo_proof || {};
    const telegram = status.phase5_telegram_notifier || {};
    const livePromotion = status.phase7_live_promotion_review || {};
    return [
        governanceRecord(
            "Phase 4 strategy approval",
            phase4.approval_event_status || phase4.approval_event?.approval_state || "missing",
            phase4.approval_event?.boundary || phase4.boundary,
            phase4.approval_event_status === "approved" || phase4.approval_event?.approval_state === "approved" ? "online" : "blocked",
            {
                event_log_written: phase4.approval_event?.event_log_correlation_present,
                boundary: phase4.approval_event?.boundary || phase4.boundary,
                href: "#reasoning"
            }
        ),
        governanceRecord(
            "Phase 5 certification",
            phase5Certification.stage_status || phase5Certification.status || "not exported",
            phase5Certification.boundary,
            phase5Certification.phase5_certified ? "online" : "pending",
            {
                event_log_written: phase5Certification.event_log_written,
                boundary: phase5Certification.boundary,
                href: "#trades"
            }
        ),
        governanceRecord(
            "Phase 6 learning approval",
            phase6.approval_state || phase6Certification.approval_state || "not requested",
            `${phase6.pending_review_action_count || phase6Certification.pending_review_action_count || 0} pending review actions; ${phase6.explicitly_deferred_action_count || phase6Certification.explicitly_deferred_action_count || 0} explicitly deferred actions.`,
            (phase6.pending_review_action_count || phase6Certification.pending_review_action_count) ? "blocked" : "pending",
            {
                event_log_written: phase6.event_log_written || phase6Certification.event_log_written,
                boundary: phase6.boundary || phase6Certification.boundary,
                href: "#trades"
            }
        ),
        governanceRecord(
            "Weekly review pack",
            phase7.q7_16_weekly_review_pack_stage_allowed ? "allowed" : "not ready",
            `${phase7.weekly_proof_trade_target || 3} verified paper trades per week where qualified setups exist; ${phase7.closed_proof_trade_count || 0}/${phase7.mature_benchmark || 100} verified paper trades.`,
            phase7.q7_16_weekly_review_pack_stage_allowed ? "online" : "pending",
            {
                event_log_written: phase7.event_log_written,
                boundary: "Weekly review packs summarize backend paper-growth state only. They cannot force trades, mark performance as mature, or approve live promotion.",
                href: "#trades"
            }
        ),
        governanceRecord(
            "Live-promotion review workflow",
            livePromotion.status || (phase7.phase7_30_day_run_complete ? "planning visible" : "not eligible"),
            livePromotion.boundary || "Live promotion remains a review workflow only until paper-growth, maturity, drawdown, postmortem, and approval gates pass.",
            livePromotion.live_capital_enabled ? "blocked" : "pending",
            {
                event_log_written: livePromotion.event_log_written,
                boundary: livePromotion.boundary || "Live promotion review cannot enable live capital from the dashboard.",
                href: "#operations"
            }
        ),
        governanceRecord(
            "Telegram send-test approval",
            telegram.send_test_approval_present ? "present" : "missing",
            `${telegram.queued_dry_run_alert_count || 0} queued dry-run alerts; ${telegram.telegram_live_notifications_allowed_count || 0} live notifications allowed.`,
            telegram.telegram_live_notifications_allowed_count ? "blocked" : "pending",
            {
                event_log_written: telegram.event_log_written,
                boundary: telegram.boundary,
                href: "#operations"
            }
        )
    ];
}

function buildGovernanceOpenActions(status = {}) {
    const notes = status.fund_manager_notes || {};
    const phase6 = status.phase6_learning_loop || {};
    const phase7 = status.phase7_demo_proof || {};
    const telegram = status.phase5_telegram_notifier || {};
    const actions = [];
    if (modelNumber(notes.suggestion_count, 0)) {
        actions.push({
            label: "Review Fund Manager suggestions",
            detail: `${notes.suggestion_count} suggestions mirrored; ${notes.accepted_count || 0} accepted; ${notes.implemented_count || 0} implemented.`,
            tone: "pending",
            href: "#operations"
        });
    }
    if (modelNumber(phase6.governance_pending_count || phase6.pending_review_action_count, 0)) {
        actions.push({
            label: "Resolve learning governance",
            detail: `${phase6.governance_pending_count || phase6.pending_review_action_count} learning review actions remain visible or deferred.`,
            tone: "blocked",
            href: "#trades"
        });
    }
    if (modelNumber(phase7.postmortem_due_count, 0)) {
        actions.push({
            label: "Review postmortem due marker",
            detail: `${phase7.postmortem_due_count} postmortem due markers need governance review before learning changes.`,
            tone: "pending",
            href: "#trades"
        });
    }
    if (!phase7.q7_16_weekly_review_pack_stage_allowed) {
        actions.push({
            label: "Wait for weekly review pack eligibility",
            detail: "Weekly review pack export is not yet allowed by backend proof state.",
            tone: "pending",
            href: "#trades"
        });
    }
    if (!telegram.send_test_approval_present) {
        actions.push({
            label: "Telegram remains dry-run",
            detail: "No private send-test approval is present; outbound member messages stay queued or dry-run.",
            tone: "pending",
            href: "#operations"
        });
    }
    return actions.length ? actions : [{
        label: "No open governance actions exported",
        detail: "The dashboard status does not expose any governance action that requires attention.",
        tone: "online",
        href: "#operations"
    }];
}

function buildGovernanceModel(status = {}) {
    const notes = status.fund_manager_notes || {};
    const comments = asArray(notes.recent_comments);
    const telegram = status.communications?.telegram || {};
    const telegramNotifier = status.phase5_telegram_notifier || {};
    const phase4 = phase4StrategyStatus(status);
    const phase6 = status.phase6_learning_loop || {};
    const phase6Certification = status.phase6_certification || {};
    const phase7 = status.phase7_demo_proof || {};
    const approvalRecords = buildGovernanceApprovalRecords(status);
    const openActions = buildGovernanceOpenActions(status);
    return {
        id: "governance",
        label: "Governance",
        question: "What comments, approvals, reviews, and communications need attention?",
        tone: openActions.some((action) => action.tone === "blocked") || asArray(phase4.certification?.certification_blockers).length ? "blocked" : "pending",
        summary: `${comments.length} recent comments; approval ${dashboardText(phase4.approval_event_status || phase4.approval_event?.approval_state, "missing")}; Telegram ${dashboardText(telegram.status, "not exported")}; ${openActions.length} open actions.`,
        comments: {
            count: comments.length,
            suggestion_count: modelNumber(notes.suggestion_count, 0),
            accepted_count: modelNumber(notes.accepted_count, 0),
            implemented_count: modelNumber(notes.implemented_count, 0),
            rejected_count: modelNumber(notes.rejected_count, 0),
            records: comments
        },
        approvals: {
            strategy_approval_state: phase4.approval_event_status || phase4.approval_event?.approval_state || "missing",
            strategy_approval_logged: Boolean(phase4.approval_event?.approval_logged || phase4.approval_logged),
            learning_approval_state: phase6.approval_state || phase6Certification.approval_state || "not requested",
            pending_review_action_count: modelNumber(phase6.pending_review_action_count || phase6Certification.pending_review_action_count, 0),
            records: approvalRecords
        },
        review_packs: {
            weekly_review_pack_state: phase7.q7_16_weekly_review_pack_stage_allowed ? "allowed" : "not ready",
            weekly_proof_trade_target: modelNumber(phase7.weekly_proof_trade_target, 3),
            current_proof_week_number: modelNumber(phase7.current_proof_week_number, 0),
            proof_week_count: modelNumber(phase7.proof_week_count, 5),
            closed_proof_trade_count: modelNumber(phase7.closed_proof_trade_count, 0),
            postmortem_due_count: modelNumber(phase7.postmortem_due_count, 0),
            boundary: "Weekly review packs summarize backend paper-growth state only. They cannot force trades, mark performance as mature, or approve live promotion."
        },
        live_promotion: {
            status: status.phase7_live_promotion_review?.status || "not eligible",
            review_workflow_visible: Boolean(status.phase7_live_promotion_review || phase7.phase7_30_day_run_complete),
            live_capital_enabled: Boolean(status.phase7_live_promotion_review?.live_capital_enabled || phase7.live_capital_enabled),
            boundary: status.phase7_live_promotion_review?.boundary || "Live promotion review cannot enable live capital from the dashboard."
        },
        communications: {
            telegram_status: telegram.status || "not exported",
            dry_run_message_count: modelNumber(telegram.dry_run_message_count, 0),
            pending_queue_count: modelNumber(telegram.pending_queue_count, 0),
            failed_count: modelNumber(telegram.failed_count, 0),
            suppressed_count: modelNumber(telegram.suppressed_count || telegramNotifier.suppressed_alert_count, 0),
            send_gate: telegram.send_gate || telegramNotifier.send_test_gate_state || "not exported",
            command_path_enabled: Boolean(telegramNotifier.telegram_command_path_enabled),
            command_path_enabled_count: modelNumber(telegramNotifier.telegram_command_path_enabled_count, 0),
            live_send_allowed_count: modelNumber(telegramNotifier.telegram_live_notifications_allowed_count || telegramNotifier.live_send_allowed_count, 0),
            recent_messages: asArray(telegram.recent_messages),
            active_message_classes: asArray(telegram.active_message_classes),
            boundary: telegram.boundary || telegramNotifier.boundary || status.communications?.boundary || "Telegram is outbound notify-only."
        },
        comment_targets: buildGovernanceCommentTargets(status),
        open_actions: openActions,
        empty_state: comments.length ? null : dashboardModelEmptyState("missing", 0, {
            title: "No governance comments loaded",
            body: "No governance comments are loaded for this dashboard status yet.",
            tone: "neutral"
        }),
        boundary: notes.boundary || status.communications?.boundary || "Governance notes only. No trade approval, order placement, or local secret access."
    };
}

function buildOverviewModel(status = {}, source = {}, sharedOperations = null, sharedModels = {}) {
    const sources = sharedModels.sources_model || buildSourcesModel(status);
    const trades = sharedModels.trades_model || buildTradesModel(status, { sources_model: sources });
    const reasoning = sharedModels.reasoning_model || buildReasoningModel(status);
    const performance = sharedModels.performance_model || buildPerformanceModel(status);
    const operations = sharedModels.operations_model || sharedOperations || buildOperationsModel(status, source, sharedModels);
    const phase7 = status.phase7_demo_proof || {};
    const paperLive = status.paper_live_certification || {};
    const activeAutomation = status.paperops_active_paper_trading_automation || {};
    const firstWeekMandate = status.paperops_first_week_paper_trade_mandate || {};
    const opportunityScan = status.paperops_opportunity_scan_cadence || {};
    const capital = status.capital || {};
    const tradeLayer = status.trade_layer || {};
    const phase4 = status.phase4_strategy || {};
    const unattendedArmed = Boolean(
        paperLive.paper_live_unattended_execution_delegation_enabled
            || activeAutomation.unattended_paper_execution_delegation_enabled
    );
    const freshSubmitCount = modelNumber(
        activeAutomation.paperops2_fresh_eligible_submit_record_count,
        0
    );
    const duplicateSubmitCount = modelNumber(
        activeAutomation.paperops2_duplicate_submit_record_count,
        0
    );
    const automationReason = dashboardText(
        paperLive.paper_live_unattended_execution_delegation_reason
            || activeAutomation.unattended_paper_execution_delegation_reason,
        "not armed"
    );
    const opportunityScanInterval = modelNumber(opportunityScan.opportunity_scan_interval_minutes, 20);
    const paperSubmitRunnerInterval = modelNumber(opportunityScan.paper_submit_runner_interval_minutes, 60);
    const opportunityScanStatus = opportunityScan.status || "not_run";
    const mandateTarget = modelNumber(firstWeekMandate.daily_target_trade_count, 0);
    const mandateSubmitted = modelNumber(firstWeekMandate.daily_submitted_count, 0);
    const mandateReady = modelNumber(firstWeekMandate.daily_ready_submit_count, 0);
    const mandateMinNotional = modelNumber(firstWeekMandate.minimum_notional_usd, 0);
    const mandateActive = Boolean(firstWeekMandate.active);
    const mandateTone = mandateActive
        ? (mandateSubmitted >= mandateTarget && mandateTarget ? "online" : "pending")
        : "pending";
    const opportunityScanTone = /invalid|blocked/i.test(opportunityScanStatus)
        ? "blocked"
        : (opportunityScan.twenty_minute_scan_ready ? "online" : "pending");
    const opportunityScanSummary = opportunityScan.recommended_next_action
        || `Refresh opportunity state every ${opportunityScanInterval} minutes; guarded paper submission stays on the ${paperSubmitRunnerInterval}-minute runner.`;
    const actionNeeded = [];
    if (sources.quorum.status !== "ok") actionNeeded.push("Review source quorum");
    if (trades.counts.postmortem_due > 0 || performance.paper_account.postmortem_due_count > 0) actionNeeded.push("Review due postmortem");
    if (operations.safety.authority_flags.length) actionNeeded.push("Investigate authority flag");
    if (operations.safety.readiness_warnings.includes("false_phase7_proof_credit")) actionNeeded.push("Reject false performance proof");
    if (!actionNeeded.length) actionNeeded.push("Continue monitoring");
    const demoProof = {
        completed_calendar_day_count: modelNumber(phase7.completed_calendar_day_count, 0),
        required_calendar_day_count: modelNumber(phase7.phase7_harness_day_count, 30),
        current_proof_week_number: modelNumber(phase7.current_proof_week_number, 0),
        proof_week_count: modelNumber(phase7.proof_week_count, 0),
        weekly_proof_trade_target: modelNumber(phase7.weekly_proof_trade_target, 3),
        qualified_setup_count: modelNumber(phase7.qualified_setup_count, 0),
        eligible_setup_count: modelNumber(phase7.eligible_setup_count, 0),
        candidate_setup_count: modelNumber(phase7.candidate_setup_count, 0),
        closed_proof_trade_count: modelNumber(phase7.closed_proof_trade_count, 0),
        mature_benchmark: modelNumber(phase7.mature_benchmark, 100),
        proof_state: phase7.proof_state || "not exported",
        proof_credit_allowed: Boolean(phase7.phase7_proof_credit_allowed)
            && modelNumber(phase7.closed_proof_trade_count, 0) >= modelNumber(phase7.mature_benchmark, 100)
            && modelNumber(phase7.completed_calendar_day_count, 0) >= modelNumber(phase7.phase7_harness_day_count, 30)
    };
    const paperPnl = performance.paper_account.total_pnl_gbp || 0;
    const reviewTone = actionNeeded[0] === "Continue monitoring" ? "online" : "blocked";
    const readouts = [
        {
            id: "sources",
            label: "Source health",
            state: `${sources.counts.online}/${sources.counts.total} online`,
            tone: sources.tone,
            summary: sources.summary
        },
        {
            id: "trade_path",
            label: "Trade path",
            state: `${trades.counts.candidate} trade ideas`,
            tone: trades.tone,
            summary: `${trades.counts.qualified_setup} potential setups; ${trades.counts.submitted_paper_order} submitted paper orders; ${trades.counts.postmortem_due} postmortems due.`
        },
        {
            id: "growth_trial",
            label: "Paper growth trial",
            state: `${formatMoney(performance.growth_trial.current_value_gbp || 0)}`,
            tone: performance.tone,
            summary: `${formatMoney(performance.growth_trial.starting_value_gbp || 100000)} to ${formatMoney(performance.growth_trial.target_value_gbp || 200000)} over ${performance.growth_trial.horizon_days || 60} days; ${formatMoney(paperPnl)} paper P&L.`
        },
        {
            id: "review_focus",
            label: "Needs review",
            state: actionNeeded[0],
            tone: reviewTone,
            summary: actionNeeded.join("; ")
        }
    ];
    const statusChips = [
        {
            id: "paper_growth",
            label: "Paper growth trial",
            value: `${formatMoney(performance.growth_trial.current_value_gbp || 0)}`,
            tone: performance.tone
        },
        {
            id: "automation",
            label: "Autonomous runner",
            value: unattendedArmed ? "Armed" : "Needs review",
            tone: unattendedArmed ? "online" : "blocked"
        },
        {
            id: "eligible_setups",
            label: "Potential setups",
            value: `${demoProof.eligible_setup_count}`,
            tone: demoProof.eligible_setup_count ? "online" : "pending"
        },
        {
            id: "candidates",
            label: "Trade ideas",
            value: `${trades.counts.candidate}`,
            tone: trades.counts.candidate ? "pending" : "online"
        },
        {
            id: "paper_orders",
            label: "Submitted paper orders",
            value: `${trades.counts.submitted_paper_order}`,
            tone: trades.counts.submitted_paper_order ? "online" : "pending"
        },
        {
            id: "postmortems",
            label: "Postmortems due",
            value: `${trades.counts.postmortem_due}`,
            tone: trades.counts.postmortem_due ? "blocked" : "online"
        }
    ];
    const nextReviewLinks = [
        {
            view_id: "trades",
            href: "#trades",
            label: "Review trades",
            reason: trades.counts.postmortem_due
                ? "A postmortem is due."
                : `${trades.counts.qualified_setup} potential setups and ${trades.counts.candidate} trade ideas.`
        },
        {
            view_id: "evidence",
            href: "#evidence",
            label: "Review evidence",
            reason: sources.quorum.status === "ok"
                ? "Source quorum is currently sufficient."
                : "Source quorum needs attention."
        },
        {
            view_id: "reasoning",
            href: "#reasoning",
            label: "Review reasoning",
            reason: `${reasoning.counts.hypotheses} hypotheses and ${reasoning.counts.evidence_packets} evidence packets.`
        },
        {
            view_id: "operations",
            href: "#operations",
            label: "Review operations",
            reason: operations.safety.authority_flags.length
                ? "Authority flags require review."
                : "Runtime is read-only from this dashboard."
        }
    ];
    const systemStatus = [
        {
            id: "mode",
            label: "Mode",
            value: status.mode === "paper" ? "Paper trading" : canonicalStatusLabel(status.mode, { fallback: "Mode unknown" }),
            tone: status.mode === "paper" ? "online" : "pending",
            summary: "The dashboard is showing paper-account operation only."
        },
        {
            id: "runtime",
            label: "Runtime",
            value: operations.runtime?.live_bridge_read_only === false ? "Review bridge" : "Read-only bridge",
            tone: operations.runtime?.live_bridge_read_only === false ? "blocked" : "online",
            summary: source?.key === "live_bridge"
                ? "Protected status endpoint is serving the dashboard."
                : "Sanitized status snapshot is serving the dashboard."
        },
        {
            id: "sources",
            label: "Sources",
            value: `${sources.counts.online}/${sources.counts.total} connected`,
            tone: sources.tone,
            summary: `${sources.quorum.replayed_source_count}/${sources.quorum.expected_source_count} required sources replayed; ${sources.counts.missing_credentials} credentials missing.`
        },
        {
            id: "trades",
            label: "Trade desk",
            value: `${trades.counts.candidate} trade ideas`,
            tone: trades.counts.postmortem_due ? "blocked" : (trades.counts.candidate ? "pending" : "online"),
            summary: `${trades.counts.observed_signal} observed signals, ${trades.counts.submitted_paper_order} submitted paper orders, ${trades.counts.open_position} open positions.`
        },
        {
            id: "automation",
            label: "Autonomous runner",
            value: unattendedArmed ? "Armed" : "Needs review",
            tone: unattendedArmed ? "online" : "blocked",
            summary: freshSubmitCount
                ? `${freshSubmitCount} fresh paper order can be submitted by the guarded ${paperSubmitRunnerInterval}-minute PaperOps runner.`
                : `${automationReason}; ${duplicateSubmitCount} already-submitted staged order protected by idempotency. The ${opportunityScanInterval}-minute scanner only refreshes candidate state.`
        },
        {
            id: "first_week_paper_mandate",
            label: "First-week paper mandate",
            value: mandateActive && mandateTarget ? `${mandateSubmitted}/${mandateTarget} today` : "Not active",
            tone: mandateTone,
            summary: mandateActive
                ? `${mandateReady} paper-only mandate slots remain ready; each slot targets at least ${formatUsd(mandateMinNotional)} notional through Alpaca Paper only.`
                : "The first-week paper-only trade mandate is outside its active calendar window."
        },
        {
            id: "opportunity_scan",
            label: "Opportunity scanner",
            value: `${opportunityScanInterval} min read-only`,
            tone: opportunityScanTone,
            summary: opportunityScanSummary
        },
        {
            id: "paper_submit",
            label: "Paper submit",
            value: paperLive.paper_live_submission_delegation_allowed
                ? "Fresh order ready"
                : (duplicateSubmitCount ? "No duplicate submit" : "Waiting"),
            tone: paperLive.paper_live_submission_delegation_allowed ? "pending" : "online",
            summary: paperLive.paper_live_submission_delegation_allowed
                ? `The next guarded ${paperSubmitRunnerInterval}-minute run may submit one fresh eligible Alpaca Paper order.`
                : `The ${opportunityScanInterval}-minute scanner cannot submit. Alpaca Paper execution remains guarded by fresh-order, duplicate-submit, and PaperOps checks.`
        }
    ];
    const sourceGroups = asArray(sources.pipelines).slice(0, 5).map((pipeline) => ({
        key: pipeline.pipeline,
        label: OPERATIONS_PIPELINE_LABELS[pipeline.pipeline] || dashboardText(pipeline.label, "Source group"),
        value: `${pipeline.online_count}/${pipeline.source_count} online`,
        tone: pipeline.status,
        summary: [
            pipeline.degraded_count ? `${pipeline.degraded_count} degraded` : null,
            pipeline.missing_credential_count ? `${pipeline.missing_credential_count} missing credentials` : null,
            pipeline.signal_influencing_count ? `${pipeline.signal_influencing_count} can influence signals` : "observation only"
        ].filter(Boolean).join("; ")
    }));
    const strategyToggles = asArray(phase4.strategy_toggles?.toggles);
    const tradingStrategies = strategyToggles.length
        ? strategyToggles.map((strategy) => ({
            key: strategy.strategy_key,
            label: dashboardText(strategy.label, strategy.strategy_key || "Strategy family"),
            value: strategy.approval_state === "approved" ? "Active for paper research" : "Needs review",
            tone: strategy.approval_state === "approved" ? "online" : "pending",
            approval_state: strategy.approval_state || "not exported",
            toggle_state: strategy.toggle_state || "not exported",
            visible_in_cockpit: Boolean(strategy.visible_in_cockpit),
            event_log_required: Boolean(strategy.event_log_required),
            execution_allowed: Boolean(strategy.execution_allowed),
            paper_order_allowed: Boolean(strategy.paper_order_allowed),
            broker_write_allowed: Boolean(strategy.broker_write_allowed),
            live_capital_enabled: Boolean(strategy.live_capital_enabled),
            boundary: strategy.boundary || "Strategy toggle visibility only; it cannot route execution.",
            summary: "Visible to Qadam's research and risk workflow; not an order route."
        }))
        : [{
            key: "strategy_status",
            label: "Strategy families",
            value: phase4.strategy_document_status === "validated" ? "Ready for review" : "Not exported",
            tone: phase4.strategy_document_status === "validated" ? "online" : "pending",
            approval_state: phase4.approval_event_status || "not exported",
            toggle_state: phase4.strategy_document_status || "not exported",
            visible_in_cockpit: false,
            event_log_required: false,
            execution_allowed: false,
            paper_order_allowed: false,
            broker_write_allowed: false,
            live_capital_enabled: false,
            boundary: phase4.boundary || phase4.no_execution_boundary || "Strategy-family metadata has not been exported in this snapshot.",
            summary: "Strategy-family metadata has not been exported in this snapshot."
        }];
    const latestLocalReview = asArray(reasoning.review_chain).find((review) => review.key === "research_analyst") || {};
    const latestStrategyReview = asArray(reasoning.review_chain).find((review) => review.key === "strategy_lead") || {};
    const latestSignalReview = asArray(reasoning.review_chain).find((review) => review.key === "signal_integrity") || {};
    const quantReview = reasoning.quant_annotation || {};
    const thoughtFeed = [
        {
            label: "Current focus",
            value: `${reasoning.counts.hypotheses} hypotheses under review`,
            tone: reasoning.tone,
            summary: `${reasoning.counts.evidence_packets} evidence packets and ${reasoning.counts.shadow_packets} research packets are feeding the review queue.`
        },
        {
            label: "Research Analyst",
            value: dashboardText(latestLocalReview.status, "No local review exported"),
            tone: latestLocalReview.status || "pending",
            summary: dashboardText(latestLocalReview.summary, "No local assessment is exported yet.")
        },
        {
            label: "Strategy Lead",
            value: dashboardText(latestStrategyReview.status, "No strategy review exported"),
            tone: latestStrategyReview.status || "pending",
            summary: dashboardText(latestStrategyReview.summary, "No Strategy Lead review is exported yet.")
        },
        {
            label: "Signal gate",
            value: dashboardText(latestSignalReview.status, "No signal review exported"),
            tone: latestSignalReview.status || "pending",
            summary: dashboardText(latestSignalReview.summary, "No signal-gate review is exported yet.")
        },
        {
            label: "Head of Quant",
            value: dashboardText(quantReview.recommendation, "hold"),
            tone: quantReview.status || "pending",
            summary: `${dashboardText(quantReview.backend, "quant model")} check; ${dashboardText(quantReview.boundary, "annotation only")}.`
        }
    ];
    const observedIdeas = asArray(tradeLayer.watching).map((item) => ({
        id: item.alert_id || item.intent_id || item.instrument || "observed_signal",
        label: item.instrument || item.symbol || "Observed signal",
        value: "Observed signal",
        tone: item.status || "pending",
        summary: item.trigger || item.chart_context || "Qadam is watching this market event."
    }));
    const candidateIdeas = asArray(tradeLayer.candidates).map((item) => ({
        id: item.intent_id || item.instrument || "candidate",
        label: item.instrument || item.strategy || "Candidate",
        value: "Candidate, not order",
        tone: item.status || "pending",
        summary: item.evidence_summary || item.catalyst || "Candidate needs review before any paper state."
    }));
    const blockedIdeas = asArray(tradeLayer.blocked).map((item) => ({
        id: item.intent_id || item.instrument || "blocked",
        label: item.instrument || item.strategy || "Blocked idea",
        value: "Blocked",
        tone: "blocked",
        summary: item.blocked_reason || item.risk_state || "Held by evidence, policy, or risk checks."
    }));
    const tradeConsiderations = [...observedIdeas, ...candidateIdeas, ...blockedIdeas].slice(0, 5);
    const paperTotal = modelNumber(
        capital.starting_balance_gbp,
        modelNumber(performance.paper_account.starting_balance_gbp, modelNumber(capital.current_balance_gbp, 100000))
    );
    const paperEquity = modelNumber(
        capital.equity_gbp ?? capital.current_balance_gbp,
        modelNumber(performance.paper_account.current_balance_gbp, paperTotal)
    );
    const paperCash = modelNumber(capital.cash_gbp, modelNumber(performance.paper_account.cash_gbp, paperEquity));
    const growthTrial = performance.growth_trial || {};
    const growthTarget = modelNumber(growthTrial.target_value_gbp, paperTotal * 2);
    const growthProgress = growthTarget > paperTotal
        ? Math.min(1, Math.max(0, (paperEquity - paperTotal) / (growthTarget - paperTotal)))
        : 0;
    const openExposure = asArray(capital.open_positions).reduce(
        (total, position) => total + modelNumber(position.notional_gbp ?? position.market_value_gbp ?? position.value_gbp, 0),
        0
    );
    const pendingExposure = [
        ...asArray(tradeLayer.staged_orders),
        ...asArray(tradeLayer.submitted_orders),
        ...asArray(capital.orders).filter((order) => !/filled|closed|cancelled|canceled/i.test(String(order.status || "")))
    ].reduce((total, order) => total + modelNumber(order.notional_gbp ?? order.risk_size_gbp ?? order.value_gbp, 0), 0);
    const deployedCapacity = openExposure + pendingExposure;
    const capacityUsedFraction = paperTotal ? Math.min(1, Math.max(0, deployedCapacity / paperTotal)) : 0;
    const paperCapacity = {
        total_gbp: paperTotal,
        equity_gbp: paperEquity,
        cash_gbp: paperCash,
        deployed_gbp: deployedCapacity,
        available_gbp: Math.max(0, paperTotal - deployedCapacity),
        used_fraction: capacityUsedFraction,
        used_pct: Math.round(capacityUsedFraction * 1000) / 10,
        total_pnl_gbp: performance.paper_account.total_pnl_gbp || 0,
        target_gbp: growthTarget,
        target_horizon_days: modelNumber(growthTrial.horizon_days, 60),
        target_progress_fraction: growthProgress,
        paper_live_operation_allowed: Boolean(growthTrial.operation_allowed),
        drawdown_pct: performance.paper_account.drawdown_pct || capital.drawdown_pct || 0,
        open_position_count: performance.paper_account.open_position_count || asArray(capital.open_positions).length,
        order_count: performance.paper_account.order_count || asArray(capital.orders).length,
        closed_trade_count: performance.paper_account.closed_paper_trade_count || asArray(capital.closed_trades).length,
        observed_at: capital.observed_at || status.generated_at || null,
        equity_curve: paperAccountEquityPoints(capital),
        tone: deployedCapacity ? "pending" : "online",
        summary: `${formatMoney(paperEquity)} current equity toward ${formatMoney(growthTarget)} target; ${formatMoney(deployedCapacity)} currently deployed from ${formatMoney(paperTotal)} starting paper capital.`
    };
    return {
        id: "overview",
        label: "Overview",
        question: "What is happening now?",
        tone: readouts.some((item) => item.tone === "blocked") ? "blocked" : (readouts.some((item) => item.tone === "degraded") ? "degraded" : "online"),
        summary: `${sources.counts.online}/${sources.counts.total} sources current; ${demoProof.eligible_setup_count} potential setups; ${trades.counts.candidate} trade ideas; ${opportunityScanInterval}-minute opportunity scan; ${formatMoney(paperEquity)} toward ${formatMoney(growthTarget)} in ${modelNumber(growthTrial.horizon_days, 60)} days; next review: ${actionNeeded[0]}.`,
        cards: readouts,
        readouts,
        status_chips: statusChips,
        review_focus: {
            state: actionNeeded[0],
            tone: reviewTone,
            summary: actionNeeded.join("; "),
            primary_href: nextReviewLinks[0]?.href || "#trades"
        },
        demo_proof: demoProof,
        system_status: systemStatus,
        data_sources_connected: sourceGroups,
        opportunity_scan_cadence: {
            status: opportunityScanStatus,
            interval_minutes: opportunityScanInterval,
            frequency_per_hour: modelNumber(opportunityScan.opportunity_scan_frequency_per_hour, 3),
            model_review_interval_minutes: modelNumber(opportunityScan.model_review_interval_minutes, 60),
            paper_submit_runner_interval_minutes: paperSubmitRunnerInterval,
            recurring_scheduler_active: Boolean(opportunityScan.twenty_minute_recurring_scheduler_active),
            recurring_scheduler_status: opportunityScan.recurring_scheduler_status || "not_run",
            trade_submission_allowed_by_scan: Boolean(opportunityScan.trade_submission_allowed_by_scan),
            fresh_eligible_submit_count: modelNumber(opportunityScan.fresh_eligible_submit_count, 0),
            duplicate_submit_count: modelNumber(opportunityScan.duplicate_submit_count, 0),
            escalation_to_hourly_runner_recommended: Boolean(opportunityScan.escalation_to_hourly_runner_recommended),
            summary: opportunityScanSummary,
            boundary: opportunityScan.boundary || "The opportunity scanner is read-only and cannot submit orders."
        },
        trading_strategies: tradingStrategies,
        thought_feed: thoughtFeed,
        trade_considerations: tradeConsiderations,
        paper_capacity: paperCapacity,
        lifecycle: trades.lifecycle,
        lifecycle_summary: `${trades.counts.qualified_setup} potential setups, ${trades.counts.candidate} trade ideas, ${trades.counts.submitted_paper_order} submitted paper orders, ${trades.counts.closed_paper_trade} closed paper trades.`,
        action_needed: actionNeeded,
        next_review_links: nextReviewLinks,
        mini_map: {
            source_model: "system_connectivity_model",
            placement: operations.system_connectivity_model.overview_scope.placement,
            node_keys: operations.system_connectivity_model.overview_scope.node_keys,
            health: operations.system_connectivity_model.authority_violations.length ? "blocked" : "online"
        },
        system_summary: "Live data -> Qadam Orchestrator -> model research -> quant/risk checks -> paper trading -> learning loop.",
        scope_note: "Use Safety Status for order authority. Overview only answers what changed and where to review next.",
        model_dependencies: {
            sources_model: sources.id || "sources",
            trades_model: trades.id || "trades",
            reasoning_model: reasoning.id || "reasoning",
            performance_model: performance.id || "performance",
            operations_model: operations.id || "operations",
            system_connectivity_model: operations.system_connectivity_model?.id || "system_connectivity_model"
        },
        boundary: "Overview is a read-only triage surface. It cannot approve, place, modify, close, fund, or verify performance credit for trades."
    };
}

function buildDashboardSafetyStripModel(status = {}, viewModels = {}) {
    const operations = viewModels.operations_model || buildOperationsModel(status);
    const performance = viewModels.performance_model || buildPerformanceModel(status);
    const capital = status.capital || performance.paper_account || {};
    const paperAuthority = status.paper_authority_reconciliation || {};
    const safety = operations.safety || {};
    const paperBalance = capital.equity_gbp ?? capital.current_balance_gbp ?? capital.starting_balance_gbp;
    const liveCapitalEnabled = Boolean(capital.live_capital_enabled || safety.live_capital_enabled);
    const writeAuthority = Boolean(capital.write_authority);
    const authorityFlags = asArray(safety.authority_flags);
    const paperSafetyBlockers = asArray(paperAuthority.safety_blockers);
    const paperOperationalBlockers = asArray(paperAuthority.operational_blockers);
    const paperOpportunityBlockers = asArray(paperAuthority.opportunity_or_risk_blockers);
    const paperCurrentBlockers = asArray(paperAuthority.current_blockers);
    const paperAuthorityStatus = paperAuthority.status || "not_exported";
    const paperAuthorityTone = paperSafetyBlockers.length
        ? "blocked"
        : (paperOperationalBlockers.length || paperOpportunityBlockers.length ? "pending" : "online");
    const tone = liveCapitalEnabled || writeAuthority || authorityFlags.length
        ? "blocked"
        : paperAuthorityTone;
    const modeLabel = status.mode === "paper"
        ? "OK - paper only"
        : canonicalStatusLabel(status.mode, { fallback: "Mode unknown" });
    const authorityHeadline = paperSafetyBlockers.length
        ? "Review safety before paper trading"
        : (
            paperAuthorityStatus === "paper_authorized_blocked_operational"
                ? "Paper authorized; runner not armed"
                : (
                    paperAuthorityStatus === "paper_authorized_waiting_for_setup"
                        ? "Paper authorized; waiting for setup"
                        : (
                            paperAuthorityStatus?.startsWith?.("paper_authorized_ready")
                                ? "Paper action ready through guarded route"
                                : "OK - paper only, read-only, live capital off"
                        )
                )
        );
    const authoritySummary = dashboardText(
        paperAuthority.why_not_trading_now,
        "Qadam can only act through guarded PaperOps paper routes when all gates pass."
    );
    const authorityBlockerLabel = paperCurrentBlockers.length
        ? paperCurrentBlockers.slice(0, 3).join(", ")
        : "no current blockers";
    return {
        id: "dashboard_safety_strip",
        tone,
        headline: tone === "blocked"
            ? "Review safety before reading the dashboard"
            : authorityHeadline,
        summary: `${authoritySummary} ${modelNumber(safety.forbidden_action_count, asArray(status.forbidden_actions).length)} safety stops; ${authorityFlags.length} authority flags; broker writes off.`,
        authority_label: paperAuthority.paper_authorized ? "Paper authority: on" : "Paper authority: off",
        authority_tone: paperAuthorityTone,
        authority_status: paperAuthorityStatus,
        authority_blocker_label: authorityBlockerLabel,
        authority_next_action: dashboardText(
            paperAuthority.next_required_action,
            "Continue monitoring guarded PaperOps status."
        ),
        mode_label: modeLabel,
        capital_label: `${formatCapitalMoney(paperBalance, capital)} paper account`,
        live_capital_label: liveCapitalEnabled ? "Live capital enabled" : "OK - live capital off",
        read_only_label: operations.runtime?.live_bridge_read_only === false ? "Bridge review" : "OK - read-only",
        ui_broker_label: "Dashboard cannot place orders",
        llm_broker_label: "AI cannot bypass risk checks",
        proof_label: "Paper growth maturity requires verified records",
        live_capital_enabled: liveCapitalEnabled,
        write_authority: writeAuthority,
        authority_flag_count: authorityFlags.length,
        boundary: "Single display strip only. It cannot approve, place, modify, resize, close, fund, or verify performance credit for trades."
    };
}

function buildQadamDashboardViewModels(status = {}, source = {}) {
    const sources = buildSourcesModel(status);
    const trades = buildTradesModel(status, { sources_model: sources });
    const reasoning = buildReasoningModel(status);
    const performance = buildPerformanceModel(status);
    const governance = buildGovernanceModel(status);
    const systemConnectivity = buildSystemConnectivityModel(status);
    const operations = buildOperationsModel(status, source, {
        system_connectivity_model: systemConnectivity,
        governance_model: governance
    });
    const sharedModels = {
        sources_model: sources,
        trades_model: trades,
        reasoning_model: reasoning,
        performance_model: performance,
        system_connectivity_model: systemConnectivity,
        operations_model: operations,
        governance_model: governance
    };
    const overview = buildOverviewModel(status, source, operations, sharedModels);
    const safetyStrip = buildDashboardSafetyStripModel(status, {
        operations_model: operations,
        performance_model: performance
    });
    const modelGraph = {
        contract: "single_shared_dashboard_view_model_bundle",
        build_order: [
            "sources_model",
            "trades_model",
            "reasoning_model",
            "performance_model",
            "governance_model",
            "system_connectivity_model",
            "operations_model",
            "overview_model",
            "safety_strip_model"
        ],
        shared_dependencies: {
            trades_model: ["sources_model"],
            operations_model: ["system_connectivity_model", "governance_model"],
            overview_model: [
                "sources_model",
                "trades_model",
                "reasoning_model",
                "performance_model",
                "operations_model",
                "system_connectivity_model"
            ],
            safety_strip_model: ["operations_model", "performance_model"]
        },
        renderer_entrypoint: "renderQadamDashboardStatus",
        renderer_uses_shared_bundle: true
    };
    return {
        schema_version: "dashboard_view_models.v1",
        model_contract_version: "dashboard_view_models.d11k.shared_bundle.v1",
        generated_at: status.generated_at || null,
        status_source: source?.key || "unknown",
        public_safe: true,
        authority_boundary: "View models are read-only projections of sanitized dashboard status. They cannot grant trading, broker, provider, Telegram, learning-write, or live-capital authority.",
        model_graph: modelGraph,
        safety_strip_model: safetyStrip,
        overview_model: overview,
        trades_model: trades,
        sources_model: sources,
        reasoning_model: reasoning,
        performance_model: performance,
        system_connectivity_model: systemConnectivity,
        operations_model: operations,
        governance_model: governance,
        safety_model: {
            authority_flags: operations.safety.authority_flags,
            readiness_warnings: operations.safety.readiness_warnings,
            authority_unchanged: operations.safety.authority_flags.length === 0,
            ui_inferred_readiness_detected: operations.safety.readiness_warnings.includes("ui_inferred_readiness_detected"),
            false_proof_credit_detected: operations.safety.readiness_warnings.includes("false_phase7_proof_credit"),
            missing_source_quorum_detected: operations.safety.readiness_warnings.includes("missing_source_quorum")
        }
    };
}

function statusFetchHeaders(source, session) {
    if (!source.requiresAuth || !session?.access_token) return {};
    return { Authorization: `Bearer ${session.access_token}` };
}

async function fetchDashboardStatus(session) {
    const failures = [];
    for (const source of STATUS_SOURCES) {
        try {
            const response = await fetch(`${source.url}?t=${Date.now()}`, {
                cache: "no-store",
                headers: statusFetchHeaders(source, session)
            });
            if (!response.ok) {
                failures.push(`${source.key}:${response.status}`);
                continue;
            }
            return {
                source,
                status: await response.json()
            };
        } catch (error) {
            failures.push(`${source.key}:${error.message || "fetch failed"}`);
        }
    }
    throw new Error(`all status sources failed: ${failures.join(", ")}`);
}

function sourceSummary(status) {
    const watching = asArray(status.watching);
    const displaySources = watching.map((source) => ({
        ...source,
        core: sourceIsCore(source),
        display_status: sourceDisplayStatus(source),
        requires_action: sourceRequiresAction(source)
    }));
    const counts = countBy(displaySources, "display_status");
    const coreSources = displaySources.filter((source) => source.core);
    const missingCredentialCount = displaySources.filter(
        (source) => source.core && source.credential_status === "missing"
    ).length;
    return [
        renderMetric("Sources", watching.length),
        renderMetric("Core OK", `${coreSources.filter((source) => source.display_status === "ok").length}/${coreSources.length}`),
        renderMetric("Needs attention", displaySources.filter((source) => source.requires_action).length),
        renderMetric("Waiting", counts.waiting || 0),
        renderMetric("Optional", counts.optional || 0),
        renderMetric("Local-only", counts["local only"] || 0),
        renderMetric("Required not configured", missingCredentialCount),
        renderMetric("Signal influence", watching.filter((source) => source.can_influence_signals).length)
    ].join("");
}

function systemMapNode(module, index) {
    const details = flowNodeDetails(module);
    return `
        <article class="flow-node system-map-node">
            <div class="node-topline">
                ${renderStatusPill(module.status)}
                <span>${String(index + 1).padStart(2, "0")} · ${htmlText(details.role, module.owner || "Qadam desk")}</span>
            </div>
            <h3>${htmlText(module.label, module.key)}</h3>
            <p class="flow-summary">${htmlText(module.current_process)}</p>
            <dl class="node-facts">
                <div>
                    <dt>Input</dt>
                    <dd>${htmlText(details.input)}</dd>
                </div>
                <div>
                    <dt>Output</dt>
                    <dd>${htmlText(details.output)}</dd>
                </div>
            </dl>
            <span class="node-authority">${htmlText(systemMapAuthorityLabel(module, details), "read only")}</span>
        </article>
    `;
}

function systemMapConnector(label) {
    return `<div class="flow-connector" aria-hidden="true"><span>${htmlText(label)}</span></div>`;
}

function systemMapLane(lane, laneIndex) {
    const nodeHtml = lane.nodes
        .map((node, nodeIndex) => {
            const globalIndex = lane.offset + nodeIndex;
            const connector = nodeIndex < lane.nodes.length - 1
                ? systemMapConnector(node.handoff || "passes state")
                : "";
            return `${systemMapNode(node, globalIndex)}${connector}`;
        })
        .join("");

    return `
        <section class="flow-lane ${statusClass(lane.tone || "neutral")}">
            <header class="flow-lane-header">
                <span>${String(laneIndex + 1).padStart(2, "0")}</span>
                <div>
                    <h3>${htmlText(lane.title)}</h3>
                    <p>${htmlText(lane.summary)}</p>
                </div>
            </header>
            <div class="flow-lane-track">${nodeHtml}</div>
            <div class="lane-handoff"><span>${htmlText(lane.handoff)}</span></div>
        </section>
    `;
}

function renderSourceReliabilityCard(state) {
    return `
        <article class="source-reliability-card ${statusClass(state.tone)}">
            <span>${htmlText(state.label)}</span>
            <strong>${htmlText(state.count)}</strong>
            <p>${htmlText(state.detail)}</p>
        </article>
    `;
}

function renderSupplementalSourceCard(source) {
    return `
        <article class="source-supplemental-card ${statusClass(source.degraded ? "degraded" : source.status)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(source.status)}
                <span>${htmlText(source.authority)}</span>
            </div>
            <h3>${htmlText(source.label)}</h3>
            <p>${htmlText(source.role)}</p>
            <div class="tag-row">
                ${renderInlineBadge(source.capability_state, source.degraded ? "degraded" : "pending")}
                ${renderInlineBadge(`provenance ${dashboardText(source.provenance_status)}`, source.provenance_status === "validated" ? "online" : "pending")}
                ${renderInlineBadge("supplemental only", "pending")}
            </div>
            <p class="mini">${htmlText(source.proof_boundary)}</p>
        </article>
    `;
}

function renderSourceSetupLink(link) {
    return `
        <a class="source-setup-link ${statusClass(link.status)}" href="${literalHtmlText(link.href)}">
            <span>${htmlText(link.stage)}</span>
            <strong>${htmlText(link.label)}</strong>
            <p>${htmlText(link.source_ref)} · ${htmlText(link.summary)}</p>
            <small>${htmlText(link.proof_boundary)}</small>
        </a>
    `;
}

function renderSourcePipelineCard(pipeline) {
    const sourceRows = asArray(pipeline.top_sources).map((source) => `
        <li>
            <strong>${htmlText(source.label)}</strong>
            <span>${htmlText(canonicalStatusLabel(source.status))} · ${htmlText(source.readiness)} · ${source.promoted_adapter ? "adapter" : "pending adapter"} · ${source.can_influence_signals ? "signal-influencing" : "evidence only"}</span>
        </li>
    `).join("");
    return `
        <article class="source-pipeline-card ${statusClass(pipeline.status)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(pipeline.status)}
                <span>${htmlText(pipeline.source_count)} sources</span>
            </div>
            <h3>${htmlText(pipeline.label)}</h3>
            <div class="summary-strip compact">
                ${renderMetric("OK", pipeline.online_count)}
                ${renderMetric("Needs attention", pipeline.degraded_count)}
                ${renderMetric("Waiting", pipeline.pending_count)}
                ${renderMetric("Optional", pipeline.optional_count)}
                ${renderMetric("Not configured", pipeline.missing_credential_count)}
                ${renderMetric("Adapter backlog", pipeline.pending_adapter_count)}
                ${renderMetric("Signal influence", pipeline.signal_influencing_count)}
            </div>
            <ul>${sourceRows}</ul>
        </article>
    `;
}

function renderEvidencePacketMiniCard(packet) {
    return `
        <article class="evidence-packet-mini-card ${statusClass(packet.status)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(packet.status)}
                <span>${htmlText(packet.trail_id)}</span>
            </div>
            <h3>${htmlText(packet.signal_id)}</h3>
            <p>${htmlText(packet.summary)}</p>
            <div class="summary-strip compact">
                ${renderMetric("Items", packet.item_count)}
                ${renderMetric("Sources", packet.sources)}
            </div>
            <p class="mini">${htmlText(packet.boundary)}</p>
        </article>
    `;
}

function renderEvidenceReviewGroup(group, bodyHtml, open = false) {
    return `
        <details class="evidence-review-group" ${open ? "open" : ""} data-evidence-review-group="${literalHtmlText(group.id)}">
            <summary>
                <strong>${htmlText(group.label)}</strong>
                <span>${htmlText(group.summary)}</span>
                <em>${htmlText(group.record_count)} records</em>
            </summary>
            <div class="evidence-review-group-body">${bodyHtml}</div>
        </details>
    `;
}

function renderSourcesWorkspace(model) {
    const groups = new Map(asArray(model.evidence_review_groups).map((group) => [group.id, group]));
    const setupGroup = groups.get("setup_evidence") || { id: "setup_evidence", label: "Setup evidence", summary: "", record_count: 0 };
    const reliabilityGroup = groups.get("source_reliability") || { id: "source_reliability", label: "Source reliability", summary: "", record_count: 0 };
    const supplementalGroup = groups.get("supplemental_context") || { id: "supplemental_context", label: "Supplemental context", summary: "", record_count: 0 };
    const packetGroup = groups.get("factual_packets") || { id: "factual_packets", label: "Factual evidence packets", summary: "", record_count: 0 };
    return `
        <section class="sources-workspace" data-sources-workspace>
            <div class="sources-workspace-head">
                <div>
                    <p class="label">Evidence workspace</p>
                    <h3>Source reliability and corroboration</h3>
                    <p>${htmlText(model.summary)} ${htmlText(model.source_to_setup_summary)}</p>
                </div>
                <div class="source-quorum-card ${statusClass(model.quorum.status)}">
                    <span>Source quorum</span>
                    <strong>${htmlText(model.quorum.status)}</strong>
                    <p>${htmlText(model.quorum.replayed_source_count)} replayed of ${htmlText(model.quorum.expected_source_count)} expected; ${htmlText(model.quorum.missing_source_count)} canonical missing.</p>
                </div>
            </div>
            <section class="evidence-consolidated-readout ${statusClass(model.tone)}" data-evidence-consolidated-readout>
                <div>
                    <p class="label">Evidence readout</p>
                    <h3>Can current observations support review?</h3>
                    <p>Use this view to separate factual evidence, supplemental context, and source weakness before reviewing a setup.</p>
                </div>
                <div class="evidence-consolidated-metrics" data-source-summary>
                    ${renderMetric("Sources", model.counts.total)}
                    ${renderMetric("Core OK", `${model.counts.core_ok}/${model.counts.core}`)}
                    ${renderMetric("Required not configured", model.counts.missing_credentials)}
                    ${renderMetric("Optional", model.counts.optional)}
                    ${renderMetric("Optional not configured", model.counts.optional_credentials)}
                    ${renderMetric("Signal influence", model.counts.signal_influencing)}
                    ${renderMetric("Yahoo Finance", asArray(model.supplemental).find((source) => source.key === "yahoo_finance")?.status || "not exported")}
                    ${renderMetric("Preference MCP", asArray(model.supplemental).find((source) => source.key === "preference_mcp")?.status || "not exported")}
                </div>
                <div class="tag-row">
                    ${renderInlineBadge(`${model.counts.evidence_packets} factual packets`, model.counts.evidence_packets ? "online" : "pending")}
                    ${renderInlineBadge(`${model.counts.source_setup_links} setup links`, model.counts.source_setup_links ? "pending" : "online")}
                    ${renderInlineBadge(`${model.counts.supplemental} supplemental inputs`, "pending")}
                    ${renderInlineBadge("sources cannot create orders", "online")}
                </div>
            </section>
            <div class="evidence-review-groups" data-evidence-review-groups>
                ${renderEvidenceReviewGroup(setupGroup, `
                    <section class="source-setup-panel">
                        <div class="overview-section-head">
                            <span>Source to setup links</span>
                            <strong>Observed and candidate records still need corroboration before paper state.</strong>
                        </div>
                        <div class="source-setup-grid">
                            ${asArray(model.source_setup_links).length
        ? asArray(model.source_setup_links).map(renderSourceSetupLink).join("")
        : `<article class="source-setup-link pending"><strong>No source-linked setups</strong><p>No active observed signal, qualified setup, or candidate is exported.</p></article>`}
                        </div>
                    </section>
                `, true)}
                ${renderEvidenceReviewGroup(reliabilityGroup, `
                    <section class="source-reliability-section">
                        <div class="overview-section-head">
                            <span>Reliability states</span>
                            <strong>Credential, heartbeat, adapter, and quorum problems in one place.</strong>
                        </div>
                        <div class="source-reliability-grid">
                            ${asArray(model.reliability).map(renderSourceReliabilityCard).join("")}
                        </div>
                    </section>
                    <section class="source-pipeline-workspace">
                        <div class="overview-section-head">
                            <span>Pipeline groups</span>
                            <strong>Reliability state by intelligence pipeline.</strong>
                        </div>
                        <div class="source-pipeline-grid">
                            ${asArray(model.pipelines).map(renderSourcePipelineCard).join("")}
                        </div>
                    </section>
                `)}
                ${renderEvidenceReviewGroup(supplementalGroup, `
                    <div class="source-supplemental-grid">
                        ${asArray(model.supplemental).map(renderSupplementalSourceCard).join("")}
                    </div>
                `)}
                ${renderEvidenceReviewGroup(packetGroup, `
                    <div class="evidence-packet-mini-grid">
                        ${asArray(model.evidence_packets).length
        ? asArray(model.evidence_packets).map(renderEvidencePacketMiniCard).join("")
        : `<article class="evidence-packet-mini-card pending"><h3>No factual evidence packets</h3><p>No evidence packets are exported in this snapshot.</p></article>`}
                    </div>
                `)}
            </div>
            <p class="mini">${htmlText(model.boundary)}</p>
        </section>
    `;
}

function renderOperationsRoleNode(role) {
    return `
        <a class="operations-role-node ${statusClass(role.status)}" href="${literalHtmlText(role.href)}">
            <span>${htmlText(role.role)}</span>
            <strong>${htmlText(role.label)}</strong>
            <p>${htmlText(role.summary)}</p>
            <small>${htmlText(role.node_count)} linked nodes · ${htmlText(role.authority)}</small>
        </a>
    `;
}

function renderOperationsFeedCluster(cluster) {
    const sources = asArray(cluster.sources).length
        ? asArray(cluster.sources).map((source) => `
            <li>
                <strong>${htmlText(source.label)}</strong>
                <span>${htmlText(source.status)} · ${htmlText(source.readiness)} · ${htmlText(source.credential_status)} · ${source.promoted_adapter ? "adapter promoted" : "adapter pending"}</span>
            </li>
        `).join("")
        : `<li><strong>${htmlText(cluster.provenance)}</strong><span>${htmlText(cluster.authority)} · source rows summarized by backend status.</span></li>`;
    return `
        <details class="operations-feed-cluster ${statusClass(cluster.status)}">
            <summary>
                <span>${htmlText(cluster.label)}</span>
                <strong>${htmlText(cluster.source_count)} sources</strong>
                ${renderStatusPill(cluster.status)}
            </summary>
            <div class="operations-feed-body">
                <div class="summary-strip compact">
                    ${renderMetric("Online", cluster.online_count || 0)}
                    ${renderMetric("Degraded", cluster.degraded_count || 0)}
                    ${renderMetric("Pending", cluster.pending_count || 0)}
                    ${renderMetric("Missing creds", cluster.missing_credential_count || 0)}
                    ${renderMetric("Adapters", cluster.adapter_ready_count || 0)}
                </div>
                <p>${htmlText(cluster.provenance)} · ${htmlText(cluster.authority)}</p>
                <ul>${sources}</ul>
            </div>
        </details>
    `;
}

function renderOperationsEdge(edge, connectivity) {
    const nodeByKey = new Map(asArray(connectivity.nodes).map((node) => [node.key, node]));
    const from = nodeByKey.get(edge.from);
    const to = nodeByKey.get(edge.to);
    return `
        <li class="${statusClass(edge.state)}">
            <strong>${htmlText(from?.label || edge.from)} -> ${htmlText(to?.label || edge.to)}</strong>
            <span>Edge state: ${htmlText(edge.state)} · ${htmlText(edge.label)} · ${htmlText(edge.authority_boundary)}</span>
        </li>
    `;
}

function renderOperationsNodeDetails(node, index) {
    const expanded = node.expanded || {};
    const dependencies = asArray(expanded.dependencies).length ? asArray(expanded.dependencies) : ["No dependencies exported"];
    const degradedReasons = asArray(expanded.degraded_reasons).length ? asArray(expanded.degraded_reasons) : ["No degraded reasons exported"];
    const eventRefs = asArray(expanded.event_log_references).length ? asArray(expanded.event_log_references) : [expanded.backend_status_path || "not exported"];
    const links = asArray(expanded.related_dashboard_links).length ? asArray(expanded.related_dashboard_links) : ["#operations"];
    return `
        <article class="flow-node system-map-node operations-map-node ${statusClass(node.health || node.status)}">
            <div class="node-topline">
                ${renderStatusPill(node.status)}
                <span>${String(index + 1).padStart(2, "0")} · ${htmlText(node.role)}</span>
            </div>
            <h3>${htmlText(node.label)}</h3>
            <p class="flow-summary">${htmlText(expanded.current_process || node.purpose)}</p>
            <dl class="node-facts">
                <div>
                    <dt>Input</dt>
                    <dd>${htmlText(node.input)}</dd>
                </div>
                <div>
                    <dt>Output</dt>
                    <dd>${htmlText(node.output)}</dd>
                </div>
            </dl>
            <details class="operations-node-diagnostics">
                <summary>Expand diagnostics</summary>
                <dl>
                    <div><dt>Purpose</dt><dd>${htmlText(expanded.purpose || node.purpose)}</dd></div>
                    <div><dt>Inputs</dt><dd>${htmlText(node.input)}</dd></div>
                    <div><dt>Outputs</dt><dd>${htmlText(node.output)}</dd></div>
                    <div><dt>Current status</dt><dd>${htmlText(expanded.current_status || node.status)}</dd></div>
                    <div><dt>Latest heartbeat</dt><dd>${htmlText(formatTime(expanded.latest_heartbeat))}</dd></div>
                    <div><dt>Dependencies</dt><dd>${dependencies.map((item) => htmlText(item)).join(", ")}</dd></div>
                    <div><dt>Degraded reasons</dt><dd>${degradedReasons.map((item) => htmlText(item)).join(", ")}</dd></div>
                    <div><dt>Event Log references</dt><dd>${eventRefs.map((item) => htmlText(item)).join(", ")}</dd></div>
                    <div><dt>Authority boundary</dt><dd>${htmlText(node.authority)}</dd></div>
                    <div><dt>Related dashboard links</dt><dd>${links.map((href) => `<a href="${literalHtmlText(href)}">${htmlText(href)}</a>`).join(" ")}</dd></div>
                </dl>
            </details>
            <span class="node-authority">${htmlText(node.authority)}</span>
        </article>
    `;
}

function renderOperationsLane(lane, connectivity, laneIndex) {
    const nodeByKey = new Map(asArray(connectivity.nodes).map((node) => [node.key, node]));
    const nodes = asArray(lane.node_keys).map((key) => nodeByKey.get(key)).filter(Boolean);
    let offset = asArray(connectivity.lanes)
        .slice(0, laneIndex)
        .reduce((total, previousLane) => total + asArray(previousLane.node_keys).length, 0);
    const nodeHtml = nodes.map((node, nodeIndex) => {
        const connector = nodeIndex < nodes.length - 1
            ? systemMapConnector(lane.handoff || "passes state")
            : "";
        const html = `${renderOperationsNodeDetails(node, offset)}${connector}`;
        offset += 1;
        return html;
    }).join("");
    return `
        <section class="flow-lane operations-lane ${statusClass(lane.tone || "pending")}">
            <header class="flow-lane-header">
                <span>${String(laneIndex + 1).padStart(2, "0")}</span>
                <div>
                    <h3>${htmlText(lane.title)}</h3>
                    <p>${htmlText(lane.summary)}</p>
                </div>
            </header>
            <div class="flow-lane-track">${nodeHtml}</div>
            <div class="lane-handoff"><span>${htmlText(lane.handoff)}</span></div>
        </section>
    `;
}

function renderOperationsDiagnosticCard(label, status, facts, tone = "pending") {
    return `
        <article class="operations-diagnostic-card ${statusClass(tone)}">
            <span>${htmlText(label)}</span>
            <strong>${htmlText(status)}</strong>
            <dl>
                ${facts.map(([key, value]) => `<div><dt>${htmlText(key)}</dt><dd>${htmlText(value)}</dd></div>`).join("")}
            </dl>
        </article>
    `;
}

function renderOperationsReviewGroup(group = {}, bodyHtml = "", open = false) {
    return `
        <details class="operations-review-group ${statusClass(group.status)}" data-operations-review-group="${literalHtmlText(group.id)}" ${open ? "open" : ""}>
            <summary>
                <strong>${htmlText(group.title)}</strong>
                <span>${htmlText(group.summary)}</span>
                <em>${htmlText(group.count || 0)} records</em>
            </summary>
            <div class="operations-review-group-body">
                ${bodyHtml}
            </div>
        </details>
    `;
}

function renderOperationsWorkspace(model = {}, status = {}) {
    const connectivity = model.system_connectivity_model || {};
    const runtime = model.runtime || {};
    const safety = model.safety || {};
    const diagnostics = model.diagnostics || {};
    const broken = model.broken_summary || {};
    const groupById = new Map(asArray(model.operations_review_groups).map((group) => [group.id, group]));
    const backendMap = status.phase5_system_map || {};
    const sourcePosture = backendMap.source_posture || {};
    const canonical = sourcePosture.canonical || {};
    const yahoo = sourcePosture.yahoo_finance || {};
    const preference = sourcePosture.preference_mcp || {};
    const guardrails = backendMap.guardrails || {};
    const paperSubmitPathCount = status.phase5_paper_trade_drill?.paper_submit_path_available_count || guardrails.paper_submit_path_available_count || 0;
    const communications = model.communications_audit || {};
    const governance = model.governance_audit || {};
    const bridgeTone = runtime.live_bridge_read_only && !safety.live_capital_enabled ? "online" : "blocked";
    const brokenItems = asArray(broken.items).length
        ? asArray(broken.items).map((item) => `<li>${htmlText(item)}</li>`).join("")
        : `<li>No broken operations path exported.</li>`;
    const hardBlockRows = asArray(model.forbidden_actions).length
        ? asArray(model.forbidden_actions).map((action) => `
            <li>
                <strong>${htmlText(action.key)}</strong>
                <span>${htmlText(action.reason)}</span>
            </li>
        `).join("")
        : `<li><strong>No hard blocks exported</strong><span>No forbidden-action records are in this snapshot.</span></li>`;
    const eventRows = asArray(model.process_events).length
        ? asArray(model.process_events).map((event) => `
            <li>
                <time>${formatTime(event.timestamp)}</time>
                <span>${htmlText(event.message)}</span>
            </li>
        `).join("")
        : `<li><time>Now</time><span>No recent runtime events are exported in this snapshot.</span></li>`;
    const governanceActionRows = asArray(governance.open_actions).length
        ? asArray(governance.open_actions).map((action) => `
            <li>
                <strong>${htmlText(action.label)}</strong>
                <span>${htmlText(action.detail)}</span>
            </li>
        `).join("")
        : `<li><strong>No open governance action</strong><span>No open Fund Manager action is exported in this snapshot.</span></li>`;
    return `
        <section class="operations-workspace" data-operations-workspace>
            <section id="operations-readout" class="operations-consolidated-readout" data-operations-consolidated-readout>
                <div class="operations-workspace-head">
                    <div>
                        <p class="label">Operations workspace</p>
                        <h3>Operations readout and full system map</h3>
                        <p>${htmlText(model.summary)} This is the read-only runtime diagnostics and full system connectivity view: bridge health, safety stops, team roles, feed plumbing, map edges, event trail, governance, and outbound communications in one place.</p>
                    </div>
                    <article class="operations-broken-card ${statusClass(broken.status)}">
                        <span>What is broken?</span>
                        <strong>${broken.item_count || 0} items</strong>
                        <ul>${brokenItems}</ul>
                    </article>
                </div>
                <div class="operations-consolidated-metrics">
                    ${renderMetric("Nodes", connectivity.node_count || 0)}
                    ${renderMetric("Bridge", runtime.live_bridge_read_only === false ? "review" : "read-only")}
                    ${renderMetric("Events", asArray(model.process_events).length)}
                    ${renderMetric("Hard blocks", safety.forbidden_action_count || 0)}
                    ${renderMetric("Authority flags", safety.authority_flags?.length || 0)}
                    ${renderMetric("Telegram queue", communications.pending_queue_count || 0)}
                    ${renderMetric("Comments", governance.comments || 0)}
                    ${renderMetric("Live capital", safety.live_capital_enabled ? "on" : "off")}
                </div>
                <div class="tag-row">
                    ${renderInlineBadge("Read-only bridge", runtime.live_bridge_read_only === false ? "blocked" : "online")}
                    ${renderInlineBadge("Sanitized status available", runtime.public_safe ? "online" : "blocked")}
                    ${renderInlineBadge("No browser shell", "online")}
                    ${renderInlineBadge(communications.command_path_enabled ? "Telegram command path enabled" : "No Telegram command path", communications.command_path_enabled ? "blocked" : "online")}
                    ${renderInlineBadge(safety.live_capital_enabled ? "Live capital enabled" : "Live capital disabled", safety.live_capital_enabled ? "blocked" : "online")}
                </div>
            </section>

            <p class="operations-safety-reference" data-operations-safety-reference>Dashboard authority is summarized once in Safety Status above. Operations below show the evidence behind that state.</p>

            <div class="operations-review-groups" data-operations-review-groups>
                ${renderOperationsReviewGroup(groupById.get("runtime_safety"), `
                    <section class="operations-diagnostics-grid" aria-label="Operations diagnostics">
                        ${renderOperationsDiagnosticCard("Bridge and snapshot", runtime.live_bridge_status || "not exported", [
        ["Endpoint", runtime.endpoint || "not exported"],
        ["Source", runtime.status_source || "not exported"],
        ["Allowed", asArray(runtime.allowed_methods).join(", ") || "none"],
        ["Forbidden", asArray(runtime.forbidden_methods).join(", ") || "none"],
        ["D1", runtime.d1_snapshot_status || "not exported"]
    ], bridgeTone)}
                        ${renderOperationsDiagnosticCard("Exporter and cache", runtime.cache_mode || "not exported", [
        ["Fallback", runtime.static_fallback || "not exported"],
        ["Max age", `${runtime.cache_max_age_seconds || 0}s`],
        ["Stale after", `${runtime.stale_after_seconds || 0}s`],
        ["Signature", runtime.signature_configured ? "configured" : runtime.publisher_status || "digest only"],
        ["Generated", formatTime(runtime.generated_at)]
    ], runtime.public_safe ? "online" : "blocked")}
                        ${renderOperationsDiagnosticCard("Module health", `${diagnostics.module_health?.total || 0} modules`, [
        ["Online", diagnostics.module_health?.online || 0],
        ["Degraded", diagnostics.module_health?.degraded || 0],
        ["Blocked", diagnostics.module_health?.blocked || 0],
        ["Pending", diagnostics.module_health?.pending || 0],
        ["Local-only", diagnostics.module_health?.local_only || 0]
    ], diagnostics.module_health?.blocked ? "blocked" : (diagnostics.module_health?.degraded ? "degraded" : "online"))}
                        ${renderOperationsDiagnosticCard("Certification diagnostics", diagnostics.phase_certification?.phase7_visibility || "not exported", [
        ["Phase 4", diagnostics.phase_certification?.phase4_certified ? "certified" : diagnostics.phase_certification?.phase4_stage || "not exported"],
        ["Phase 5", diagnostics.phase_certification?.phase5_certified ? "certified" : "not certified"],
        ["Phase 6", diagnostics.phase_certification?.phase6_certified ? "certified" : "not certified"],
        ["Paper growth", diagnostics.phase_certification?.phase7_certified ? "certified" : diagnostics.phase_certification?.phase7_visibility || "visible"],
        ["Authority", "read-only diagnostics"]
    ], "pending")}
                        ${renderOperationsDiagnosticCard("Kill-switch ledger", diagnostics.kill_switch?.status || "not exported", [
        ["Total", diagnostics.kill_switch?.total_count || 0],
        ["Active", diagnostics.kill_switch?.active_count || 0],
        ["Blocking", diagnostics.kill_switch?.blocking_count || 0],
        ["Event Log", diagnostics.kill_switch?.event_log_written ? "written" : "not exported"],
        ["Boundary", "cannot mutate from dashboard"]
    ], diagnostics.kill_switch?.blocking_count ? "blocked" : "online")}
                    </section>
                    <section class="operations-safety-list">
                        <div class="overview-section-head">
                            <span>Hard safety stops</span>
                            <strong>Safety stops are reported here, not unlocked here.</strong>
                        </div>
                        <ul class="status-list">${hardBlockRows}</ul>
                    </section>
                `, true)}

                ${renderOperationsReviewGroup(groupById.get("team_data_plumbing"), `
                    <section class="operations-role-spine" aria-label="Operations role spine">
                        <div class="overview-section-head">
                            <span>First-class operating roles</span>
                            <strong>Human oversight, live data feeds, orchestrator, analysts, quant, risk gates, paper trading, and learning loop.</strong>
                        </div>
                        <div class="operations-role-grid">
                            ${asArray(model.role_spine).map(renderOperationsRoleNode).join("")}
                        </div>
                    </section>
                    <section class="operations-feed-clusters" aria-label="Live data feed clusters">
                        <div class="overview-section-head">
                            <span>Live data feed clusters</span>
                            <strong>Five intelligence pipelines plus source provenance and supplemental adapters.</strong>
                        </div>
                        <div class="operations-feed-grid">
                            ${asArray(connectivity.feed_clusters).map(renderOperationsFeedCluster).join("")}
                        </div>
                    </section>
                `)}

                ${renderOperationsReviewGroup(groupById.get("system_map_event_trail"), `
                    <section class="operations-full-map" data-phase5-system-map aria-label="Full expandable system map">
                        <div class="operations-full-map-head">
                            <div>
                                <p class="label">Q5-13 Functional System Map Dashboard</p>
                                <h3>Full system map</h3>
                                <p>${htmlText(connectivity.boundary)} Advanced phase labels and raw operational terms are intentionally kept in Operations.</p>
                            </div>
                            <div class="summary-strip compact">
                                ${renderMetric("Nodes", backendMap.node_count || connectivity.node_count || 0)}
                                ${renderMetric("Layer B", backendMap.layer_b_node_count || 0)}
                                ${renderMetric("Lanes", backendMap.lane_count || connectivity.lane_count || 0)}
                                ${renderMetric("Backend parity", `${backendMap.backend_parity_error_count || 0} errors`)}
                                ${renderMetric("Unsafe controls", backendMap.unsafe_control_count || 0)}
                                ${renderMetric("Event Log", backendMap.event_log_written ? "written" : "pending")}
                            </div>
                        </div>
                        <div class="tag-row">
                            ${renderInlineBadge(`canonical sources ${canonical.replayed_source_count || 0}/${canonical.expected_source_count || 0}`, (canonical.missing_source_count || 0) ? "degraded" : "online")}
                            ${renderInlineBadge(`Yahoo Finance ${dashboardText(yahoo.role || "supplemental market confirmation only")}`, "pending")}
                            ${renderInlineBadge(`Preference/PREF MCP ${dashboardText(preference.status || "not exported")}`, preference.source_36 ? "blocked" : "pending")}
                            ${renderInlineBadge(guardrails.live_capital_enabled ? "live capital enabled" : "live capital disabled", guardrails.live_capital_enabled ? "blocked" : "online")}
                            ${renderInlineBadge(`paper submit path ${paperSubmitPathCount}`, paperSubmitPathCount ? "online" : "blocked")}
                            ${renderInlineBadge(guardrails.dashboard_claims_trading_now ? "dashboard says trading" : "dashboard does not say trading", guardrails.dashboard_claims_trading_now ? "blocked" : "online")}
                        </div>
                        <div class="operations-edge-legend">
                            <span>Edge state</span>
                            ${["active", "shadow/context-only", "degraded", "locked", "blocked"].map((state) => renderInlineBadge(state, state)).join("")}
                        </div>
                        <ul class="operations-edge-list">
                            ${asArray(connectivity.edges).slice(0, 14).map((edge) => renderOperationsEdge(edge, connectivity)).join("")}
                        </ul>
                        <div class="system-flow-diagram operations-flow-diagram">
                            ${asArray(connectivity.lanes).map((lane, laneIndex) => renderOperationsLane(lane, connectivity, laneIndex)).join("")}
                            <div class="flow-return-loop">
                                <strong>Closed-loop rule</strong>
                                <span>Every observation, hypothesis, risk decision, paper state, comment, and postmortem returns to the Event Log before it changes Qadam.</span>
                            </div>
                        </div>
                    </section>
                    <section class="operations-event-trail">
                        <div class="overview-section-head">
                            <span>Recent runtime events</span>
                            <strong>Process console merged into Operations; still read-only and not shell access.</strong>
                        </div>
                        <ol class="console-feed">${eventRows}</ol>
                    </section>
                `, true)}

                ${renderOperationsReviewGroup(groupById.get("governance_comms_audit"), `
                    <section class="operations-governance-audit">
                        <div class="overview-section-head">
                            <span>Governance and outbound communications</span>
                            <strong>Fund Manager review and Telegram state without separate duplicate cards.</strong>
                        </div>
                        <div class="summary-strip compact">
                            ${renderMetric("Telegram", communications.status || "not exported")}
                            ${renderMetric("Dry-run", communications.dry_run_message_count || 0)}
                            ${renderMetric("Queued", communications.pending_queue_count || 0)}
                            ${renderMetric("Failed", communications.failed_count || 0)}
                            ${renderMetric("Suppressed", communications.suppressed_count || 0)}
                            ${renderMetric("Live sends", communications.live_send_allowed_count || 0)}
                            ${renderMetric("Comments", governance.comments || 0)}
                            ${renderMetric("Approval", governance.approval || "missing")}
                        </div>
                        <div class="tag-row">
                            ${renderInlineBadge(communications.command_path_enabled ? "command path enabled" : "outbound notify-only", communications.command_path_enabled ? "blocked" : "online")}
                            ${renderInlineBadge(communications.live_send_allowed_count ? "live send allowed" : "live send disabled", communications.live_send_allowed_count ? "blocked" : "online")}
                            ${renderInlineBadge(`send gate ${dashboardText(communications.send_gate || "not exported")}`, "pending")}
                            ${renderInlineBadge(`weekly review ${dashboardText(governance.weekly_review || "not ready")}`, "pending")}
                            ${renderInlineBadge(`live promotion ${dashboardText(governance.live_promotion || "not eligible")}`, "pending")}
                        </div>
                        <ul class="operations-action-list">${governanceActionRows}</ul>
                        <p class="mini">${htmlText(communications.boundary)} ${htmlText(governance.boundary)}</p>
                    </section>
                `)}
            </div>

            <p class="mini">${htmlText(model.boundary)}</p>
        </section>
    `;
}

function renderFundModel(status, source) {
    const target = dashboardQuery("[data-fund-model]");
    if (!target) return;
    const cognition = status.cognition || {};
    const phase2Cycle = cognition.phase2_shadow_cycle || {};
    const tradeLayer = status.trade_layer || {};
    const capital = status.capital || {};
    const communications = status.communications?.telegram || {};
    const sourceMode = source?.key === "live_bridge" ? "live bridge" : "snapshot";
    const cards = [
        {
            kicker: "Fund Manager",
            title: "You supervise the fund",
            body: "Review the operating map, challenge ideas, add governance comments, and decide whether Qadam is mature enough to advance.",
            metric: `${status.mode || "paper"} mode · ${sourceMode}`
        },
        {
            kicker: "Orchestrator",
            title: "Python records the system",
            body: "The orchestrator converts source, model, and trade events into sanitized dashboard state. If it is not logged, it does not count.",
            metric: `${asArray(status.process_console).length} recent events`
        },
        {
            kicker: "Analysts",
            title: "Local and frontier models research",
            body: "The Research Analyst compresses noise locally. The Strategy Lead challenges only after evidence exists.",
            metric: `${asArray(cognition.hypotheses).length} hypotheses · ${asArray(cognition.evidence_packets).length} packets`
        },
        {
            kicker: "Quant + Risk",
            title: "Models inform, gates decide",
            body: "The Head of Quant is a bounded oracle. Risk controls block stale, weak, oversized, or unauthorized ideas.",
            metric: `${asArray(tradeLayer.blocked).length} blocked · live capital ${capital.live_capital_enabled ? "enabled" : "off"}`
        },
        {
            kicker: "Paper trading",
            title: "Ideas become paper trades only",
            body: "Observed signals and trade ideas are not orders. The paper account shows paper lifecycle states; verified paper trades are tracked separately.",
            metric: `${asArray(tradeLayer.candidates).length} trade ideas · ${communications.status || "comms pending"} comms`
        }
    ];
    target.innerHTML = cards.map((card) => `
        <article class="fund-model-card">
            <span>${htmlText(card.kicker)}</span>
            <h3>${htmlText(card.title)}</h3>
            <p>${htmlText(card.body)}</p>
            <small>${htmlText(card.metric)}</small>
        </article>
    `).join("");
}

function renderFlowMap(status, source, viewModels) {
    const target = dashboardQuery("[data-flow-map]");
    if (target) {
        const operations = viewModels?.operations_model || buildOperationsModel(status, source);
        target.innerHTML = renderOperationsWorkspace(operations, status);
        return;
    }
    const backendMap = status.phase5_system_map || {};
    if (backendMap.status === "ok" && asArray(backendMap.nodes).length && target) {
        const nodeByKey = new Map(asArray(backendMap.nodes).map((node) => [node.key, node]));
        let offset = 0;
        const lanes = asArray(backendMap.lanes).map((lane) => {
            const nodes = asArray(lane.node_keys).map((key) => nodeByKey.get(key)).filter(Boolean);
            const hydrated = { ...lane, nodes, offset };
            offset += nodes.length;
            return hydrated;
        }).filter((lane) => lane.nodes.length);
        const sourcePosture = backendMap.source_posture || {};
        const canonical = sourcePosture.canonical || {};
        const yahoo = sourcePosture.yahoo_finance || {};
        const preference = sourcePosture.preference_mcp || {};
        const guardrails = backendMap.guardrails || {};
        target.innerHTML = `
            <section class="trade-intent-section" data-phase5-system-map>
                <p class="label">Q5-13 Functional System Map Dashboard</p>
                <div class="summary-strip compact">
                    ${renderMetric("Nodes", backendMap.node_count || 0)}
                    ${renderMetric("Layer B", backendMap.layer_b_node_count || 0)}
                    ${renderMetric("Lanes", backendMap.lane_count || 0)}
                    ${renderMetric("Backend parity", `${backendMap.backend_parity_error_count || 0} errors`)}
                    ${renderMetric("Unsafe controls", backendMap.unsafe_control_count || 0)}
                    ${renderMetric("Event Log", backendMap.event_log_written ? "written" : "pending")}
                </div>
                <div class="tag-row">
                    ${renderInlineBadge(`canonical sources ${canonical.replayed_source_count || 0}/${canonical.expected_source_count || 0}`, (canonical.missing_source_count || 0) ? "degraded" : "online")}
                    ${renderInlineBadge(`Yahoo Finance ${dashboardText(yahoo.role || "supplemental")}`, "pending")}
                    ${renderInlineBadge(`Preference/PREF MCP ${dashboardText(preference.status || "not_exported")}`, preference.source_36 ? "blocked" : "pending")}
                    ${renderInlineBadge(guardrails.live_capital_enabled ? "live capital enabled" : "live capital disabled", guardrails.live_capital_enabled ? "blocked" : "online")}
                    ${renderInlineBadge(`paper submit path ${guardrails.paper_submit_path_available_count || 0}`, guardrails.paper_submit_path_available_count ? "online" : "blocked")}
                    ${renderInlineBadge(guardrails.dashboard_claims_trading_now ? "dashboard says trading" : "dashboard does not say trading", guardrails.dashboard_claims_trading_now ? "blocked" : "online")}
                </div>
                <p class="mini">${htmlText(backendMap.boundary, "The system map is read-only and sanitized for the dashboard.")}</p>
            </section>
            <div class="system-flow-diagram">
                ${lanes.map(systemMapLane).join("")}
                <div class="flow-return-loop">
                    <strong>Closed-loop rule</strong>
                    <span>Every observation, hypothesis, risk decision, paper state, comment, and postmortem returns to the Event Log before it changes Qadam.</span>
                </div>
            </div>
        `;
        return;
    }
    const tradeLayer = status.trade_layer || {};
    const tradeSummary = tradeLayer.summary || {};
    const telegram = status.communications?.telegram || {};
    const liveBridge = status.live_bridge || {};
    const capital = status.capital || {};
    const notes = status.fund_manager_notes || {};
    const watching = asArray(status.watching);
    const candidates = asArray(tradeLayer.candidates);
    const blocked = asArray(tradeLayer.blocked);
    const tradeIntentCount = tradeSummary.intent_count || 0;
    const tradeCandidateCount = candidates.length;
    const blockedTradeCount = blocked.length;
    const observedSignals = asArray(tradeLayer.watching);
    const closedTrades = asArray(capital.closed_trades);
    const postmortemsDue = asArray(capital.postmortems_due);
    const postmortemsComplete = asArray(capital.postmortems_complete);
    const mapNodes = [
        {
            key: "watching",
            label: "Watched Sources",
            owner: "Source Registry",
            status: watching.length ? "online" : "pending",
            current_process: `${watching.length} sources in the dashboard status`,
            authority: "read_only",
            handoff: "observed facts"
        },
        {
            ...(findModule(status, "event_log") || {
                key: "event_log",
                label: "Event Log",
                owner: "System memory",
                status: "local_only",
                current_process: "Local append-only runtime state",
                authority: "source_of_truth"
            }),
            handoff: "logged state"
        },
        {
            key: "live_bridge",
            label: "Secure Live Bridge",
            owner: "qadam.trade API",
            status: liveBridge.status === "read_only_ready" ? "online" : (liveBridge.status || "pending"),
            current_process: `${asArray(liveBridge.allowed_methods).join("/")} status only · fallback ${liveBridge.static_fallback || "static snapshot"}`,
            authority: liveBridge.browser_authority || "read_only",
            handoff: "sanitized dashboard state"
        },
        {
            key: "worldview",
            label: "Worldview Lens",
            owner: "Private Edge Layer",
            status: status.decision_philosophy?.status === "ok" ? "online" : "pending",
            current_process: `${status.decision_philosophy?.foundational_prior_count || 0} foundational priors shaping questions, not evidence`,
            authority: "prior_only",
            handoff: "questions, not evidence"
        },
        {
            ...(findModule(status, "research_analyst") || {
                key: "research_analyst",
                label: "Research Analyst",
                owner: "Local LLM",
                status: "pending",
                current_process: "Waiting for local triage heartbeat",
                authority: "shadow_only"
            }),
            handoff: "shadow analysis"
        },
        {
            ...(findModule(status, "strategy_lead") || {
                key: "strategy_lead",
                label: "Strategy Lead",
                owner: "Frontier model",
                status: "pending",
                current_process: "Waiting for evidence packets",
                authority: "non_executable"
            }),
            handoff: "challenge notes"
        },
        {
            ...(findModule(status, "head_of_quant") || {
                key: "head_of_quant",
                label: "Head of Quant",
                owner: "Quantum / classical oracle",
                status: "deferred",
                current_process: "No real-time role",
                authority: "weekly_oracle"
            }),
            handoff: "bounded oracle check"
        },
        {
            ...(findModule(status, "shadow_intelligence") || {
                key: "shadow_intelligence",
                label: "Shadow Intelligence",
                owner: "Research queue",
                status: "pending",
                current_process: "Hypotheses remain non-executable",
                authority: "shadow_only"
            }),
            handoff: "hypothesis package"
        },
        {
            ...(findModule(status, "signal_integrity_gate") || {
                key: "signal_integrity_gate",
                label: "Signal Integrity Gate",
                owner: "Signal Auditor",
                status: "pending",
                current_process: "Auditing shadow signals without trade authority",
                authority: "non_executable"
            }),
            handoff: "block or hold"
        },
        {
            ...(findModule(status, "risk_agent") || {
                key: "risk_agent",
                label: "Risk Agent",
                owner: "Policy Router",
                status: "pending",
                current_process: "Reviewing policy without order authority",
                authority: "read_only_policy_router"
            }),
            handoff: "policy hold"
        },
        {
            ...(findModule(status, "execution_policy") || {
                key: "execution_policy",
                label: "Execution Policy",
                owner: "Kill Switches",
                status: "blocked",
                current_process: "Kill switches and staged orders are read-only",
                authority: "read_only_execution_policy"
            }),
            handoff: "kill-switch hold"
        },
        {
            ...(findModule(status, "staged_order_contract") || {
                key: "staged_order_contract",
                label: "Staged Order Contract",
                owner: "Paper Order Gate",
                status: "blocked",
                current_process: "Disabled paper-order staging checks",
                authority: "disabled_staged_order_contract"
            }),
            handoff: "staging blocked"
        },
        {
            ...(findModule(status, "broker_reconciliation") || {
                key: "broker_reconciliation",
                label: "Broker Reconciliation",
                owner: "Paper Order Gate",
                status: "blocked",
                current_process: "Read-only broker echo and reconciliation checks",
                authority: "read_only_broker_reconciliation"
            }),
            handoff: "submit blocked"
        },
        {
            ...(findModule(status, "paper_submit_receipt") || {
                key: "paper_submit_receipt",
                label: "Paper Submit Receipt",
                owner: "Paper Order Gate",
                status: "blocked",
                current_process: "Dry-run receipt checks without broker POST",
                authority: "dry_run_receipt_only"
            }),
            handoff: "dry-run receipt only"
        },
        {
            ...(findModule(status, "execution_registry") || {
                key: "execution_registry",
                label: "Execution Registry",
                owner: "Risk Agent",
                status: "blocked",
                current_process: "Broker writes and live capital blocked",
                authority: "fail_closed"
            }),
            handoff: "broker route blocked"
        },
        {
            key: "trade_layer",
            label: "Trade Layer",
            owner: "Paper Trial",
            status: tradeLayer.store_status === "ok" ? "online" : "degraded",
            current_process: `${observedSignals.length} observed · ${tradeIntentCount} intents · ${tradeCandidateCount} candidates · ${blockedTradeCount} blocked`,
            authority: "write_blocked",
            handoff: "paper state"
        },
        {
            key: "paper_account",
            label: "Paper Account Mirror",
            owner: "Money",
            status: capital.mirror_status === "ok" ? "online" : (capital.mirror_status || "pending"),
            current_process: `${formatMoney(capital.current_balance_gbp)} current · ${capital.open_position_count || 0} open · ${capital.closed_trade_count || 0} closed`,
            authority: capital.write_authority ? "write_enabled" : "read_only",
            handoff: "closed paper outcomes"
        },
        {
            key: "postmortem_loop",
            label: "Postmortem Loop",
            owner: "Knowledge Graph",
            status: postmortemsDue.length ? "pending" : "waiting",
            current_process: `${postmortemsDue.length} due · ${postmortemsComplete.length} complete · ${closedTrades.length} closed trades`,
            authority: "after_action_review",
            handoff: "lessons return to memory"
        },
        {
            key: "telegram_bot",
            label: "Telegram Bot",
            owner: "Fund Manager Interface",
            status: telegram.status === "dry_run" ? "dry run" : (telegram.status || "disabled"),
            current_process: `${telegram.pending_queue_count || 0} queued · ${telegram.sent_count || 0} sent · ${formatTime(telegram.last_sent_time)}`,
            authority: "notify_only",
            handoff: "member visibility"
        },
        {
            key: "fund_manager_forum",
            label: "Fund Manager Forum",
            owner: "Governance",
            status: notes.status === "ok" ? "online" : (notes.status || "pending"),
            current_process: `${notes.comment_count || 0} governance notes · ${notes.implemented_count || 0} implemented`,
            authority: "governance_only",
            handoff: "improvement notes"
        }
    ].filter(Boolean);

    let offset = 0;
    const makeLane = (title, summary, handoff, tone, keys) => {
        const nodes = keys.map((key) => mapNodes.find((node) => node.key === key)).filter(Boolean);
        const lane = { title, summary, handoff, tone, nodes, offset };
        offset += nodes.length;
        return lane;
    };

    const lanes = [
        makeLane(
            "Observation",
            "World and market inputs enter as observations only.",
            "Observed facts must be logged before they count.",
            "online",
            ["watching"]
        ),
        makeLane(
            "System Memory",
            "The orchestrator records state and exposes only a safe dashboard mirror.",
            "Logged state becomes dashboard state and research input.",
            "online",
            ["event_log", "live_bridge"]
        ),
        makeLane(
            "Research",
            "Private priors and models shape questions and hypotheses without execution authority.",
            "Research outputs become challenge notes and evidence packets.",
            "pending",
            ["worldview", "research_analyst", "strategy_lead", "shadow_intelligence", "signal_integrity_gate"]
        ),
        makeLane(
            "Quant + Risk",
            "Bounded modelling can inform a gate; risk decides whether an idea may continue.",
            "Only passed gates can become paper-trial state.",
            "blocked",
            ["head_of_quant", "risk_agent", "execution_policy", "staged_order_contract", "broker_reconciliation", "paper_submit_receipt", "execution_registry"]
        ),
        makeLane(
            "Paper Trial",
            "Trade ideas become paper trades only after gates; outcomes return to learning.",
            "Closed paper outcomes and lessons return to memory.",
            "online",
            ["trade_layer", "paper_account", "postmortem_loop"]
        ),
        makeLane(
            "Members",
            "Founding Fund Managers receive notifications and leave governance comments.",
            "Human notes improve the system without creating broker authority.",
            "pending",
            ["telegram_bot", "fund_manager_forum"]
        )
    ].filter((lane) => lane.nodes.length);

    if (target) {
        target.innerHTML = `
            <div class="system-flow-diagram">
                ${lanes.map(systemMapLane).join("")}
                <div class="flow-return-loop">
                    <strong>Closed-loop rule</strong>
                    <span>Every observation, hypothesis, risk decision, paper state, comment, and postmortem returns to the Event Log before it changes Qadam.</span>
                </div>
            </div>
        `;
    }
}

function tradeEventTimestamp(record = {}) {
    return record.closed_at
        || record.filled_at
        || record.submitted_at
        || record.opened_at
        || record.created_at
        || record.updated_at
        || record.observed_at
        || record.received_at
        || null;
}

function pushTradeTimelineEvent(events, source = {}, defaults = {}) {
    const label = dashboardText(
        source.instrument_name
            || source.instrument
            || source.symbol
            || source.asset
            || source.market
            || source.strategy
            || source.title
            || defaults.label,
        defaults.label || "Paper trade event"
    );
    const detail = dashboardText(
        defaults.detail
            || source.candidate_watchlist_context
            || source.setup_type
            || source.status
            || source.direction
            || source.close_reason
            || source.blocked_reason,
        "status unknown"
    );
    const timestamp = tradeEventTimestamp(source);
    events.push({
        id: [
            defaults.kind || "event",
            source.order_id || source.trade_id || source.intent_id || source.alert_id || source.event_id || label,
            timestamp || "no_time"
        ].join(":"),
        kind: defaults.kind || "event",
        label,
        detail,
        timestamp,
        tone: defaults.tone || source.status || "pending"
    });
}

function buildTradeTimelineTokens(status = {}) {
    const capital = status.capital || {};
    const tradeLayer = status.trade_layer || {};
    const events = [];
    const money = (value) => formatCapitalMoney(value, capital);

    asArray(capital.closed_trades).forEach((trade) => pushTradeTimelineEvent(events, trade, {
        kind: "closed",
        detail: `${money(trade.realized_pnl_gbp)} realized · ${dashboardText(trade.postmortem_status, "postmortem unknown")}`,
        tone: modelNumber(trade.realized_pnl_gbp, 0) < 0 ? "degraded" : "online"
    }));
    asArray(capital.open_positions).forEach((position) => pushTradeTimelineEvent(events, position, {
        kind: "open",
        detail: `${dashboardText(position.direction, "open")} · ${money(position.unrealized_pnl_gbp)} unrealized`,
        tone: modelNumber(position.unrealized_pnl_gbp, 0) < 0 ? "degraded" : "online"
    }));
    asArray(capital.orders).forEach((order) => pushTradeTimelineEvent(events, order, {
        kind: dashboardText(order.status, "order"),
        detail: `${dashboardText(order.direction, "order")} ${dashboardText(order.order_type, "paper")} · ${money(order.notional_gbp)}`,
        tone: /filled|submitted|accepted/i.test(String(order.status || "")) ? "online" : "pending"
    }));
    asArray(tradeLayer.submitted_orders).forEach((order) => pushTradeTimelineEvent(events, order, {
        kind: "submitted",
        detail: `${dashboardText(order.direction, "paper")} · ${money(order.notional_gbp || order.risk_size_gbp)}`,
        tone: "online"
    }));
    asArray(tradeLayer.staged_orders).forEach((order) => pushTradeTimelineEvent(events, order, {
        kind: "staged",
        detail: `${dashboardText(order.direction, "paper")} · staged only`,
        tone: "pending"
    }));

    asArray(tradeLayer.candidates).forEach((candidate) => pushTradeTimelineEvent(events, candidate, {
        kind: "candidate",
        detail: "candidate, not order",
        tone: "pending"
    }));
    asArray(tradeLayer.blocked).forEach((blocked) => pushTradeTimelineEvent(events, blocked, {
        kind: "blocked",
        detail: dashboardText(blocked.blocked_reason, "blocked before order"),
        tone: "blocked"
    }));
    asArray(status.tradingview_mcp?.technical_contexts).forEach((context) => pushTradeTimelineEvent(events, context, {
        kind: "watch",
        detail: dashboardText(context.candidate_watchlist_context || context.setup_type, "technical context only"),
        tone: context.trade_candidate_created ? "pending" : "online"
    }));

    const unique = new Map();
    events.forEach((event) => {
        if (!unique.has(event.id)) unique.set(event.id, event);
    });

    const sorted = [...unique.values()]
        .sort((a, b) => {
            const aTime = a.timestamp ? new Date(a.timestamp).getTime() : 0;
            const bTime = b.timestamp ? new Date(b.timestamp).getTime() : 0;
            return (Number.isFinite(bTime) ? bTime : 0) - (Number.isFinite(aTime) ? aTime : 0);
        });
    const limited = sorted.slice(0, 5);
    const reviewEvent = sorted.find((event) => /crude oil/i.test(`${event.label} ${event.detail}`))
        || sorted.find((event) => event.kind === "candidate" || event.kind === "blocked" || event.kind === "watch");
    if (reviewEvent && !limited.some((event) => event.id === reviewEvent.id)) {
        limited[limited.length ? limited.length - 1 : 0] = reviewEvent;
    }
    return limited;
}

function buildBalanceTickerModel(status = {}, viewModels = {}) {
    const capital = status.capital || {};
    const performance = viewModels.performance_model || buildPerformanceModel(status);
    const account = performance.paper_account || {};
    const equity = modelNumber(
        capital.equity_gbp ?? capital.current_balance_gbp ?? account.current_balance_gbp,
        modelNumber(account.current_balance_gbp, 0)
    );
    const starting = modelNumber(
        capital.starting_balance_gbp ?? account.starting_balance_gbp,
        equity
    );
    const realized = modelNumber(capital.realized_pnl_gbp ?? account.realized_pnl_gbp, 0);
    const unrealized = modelNumber(capital.unrealized_pnl_gbp ?? account.unrealized_pnl_gbp, 0);
    const totalPnl = modelNumber(account.total_pnl_gbp, realized + unrealized);
    const drawdown = modelNumber(capital.drawdown_pct ?? account.drawdown_pct, 0);
    const openPositions = modelNumber(capital.open_position_count, asArray(capital.open_positions).length);
    const orders = modelNumber(capital.order_count, asArray(capital.orders).length);
    const closedTrades = modelNumber(capital.closed_trade_count, asArray(capital.closed_trades).length);
    const liveCapitalEnabled = Boolean(capital.live_capital_enabled);
    const writeAuthority = Boolean(capital.write_authority);
    const tone = liveCapitalEnabled || writeAuthority
        ? "blocked"
        : (totalPnl < 0 || drawdown > 0 ? "degraded" : "online");
    const changePct = starting ? ((equity - starting) / starting) * 100 : 0;
    return {
        equity,
        starting,
        total_pnl_gbp: totalPnl,
        display_currency: capitalCurrency(capital),
        drawdown_pct: drawdown,
        change_pct: changePct,
        open_position_count: openPositions,
        order_count: orders,
        closed_trade_count: closedTrades,
        observed_at: capital.observed_at || status.generated_at,
        tone,
        timeline: buildTradeTimelineTokens(status),
        boundary: capital.boundary || "Read-only paper account mirror."
    };
}

function renderBalanceTicker(status, viewModels = {}) {
    const model = buildBalanceTickerModel(status, viewModels);
    const ticker = dashboardQuery("[data-balance-ticker]");
    if (ticker) {
        ["online", "pending", "degraded", "blocked"].forEach((name) => ticker.classList.remove(name));
        ticker.classList.add(statusClass(model.tone));
        ticker.innerHTML = `
            <span>Paper balance</span>
            <strong>${htmlText(formatMoney(model.equity, model.display_currency))}</strong>
            <em>${htmlText(formatMoney(model.total_pnl_gbp, model.display_currency))} P&L · ${htmlText(formatPercent(model.drawdown_pct))} DD · ${htmlText(model.closed_trade_count)} closed</em>
        `;
        ticker.setAttribute(
            "title",
            `${formatMoney(model.equity, model.display_currency)} equity; ${formatMoney(model.total_pnl_gbp, model.display_currency)} P&L; ${formatPercent(model.drawdown_pct)} drawdown; observed ${formatTime(model.observed_at)}.`
        );
    }

    const rail = dashboardQuery("[data-trade-toast-rail]");
    if (!rail) return;
    const events = asArray(model.timeline);
    rail.innerHTML = events.length
        ? events.map((event) => `
            <span class="trade-toast-token ${statusClass(event.tone)}" title="${literalHtmlText(`${event.kind}: ${event.label} · ${event.detail} · ${formatTime(event.timestamp)}`)}">
                <em>${htmlText(event.kind)}</em>
                <strong>${htmlText(event.label)}</strong>
                <em>${htmlText(formatTime(event.timestamp))}</em>
            </span>
        `).join("")
        : `<span class="trade-toast-token pending">No paper trade timeline yet</span>`;
}

function renderSnapshotMeta(status, source) {
    const capital = status.capital || {};
    const d1Snapshot = status.d1_snapshot || {};
    const liveBridge = status.live_bridge || {};
    const generatedAt = formatTime(status.generated_at);
    const sourceLabel = source?.label || "static snapshot";
    const bridgeSourceLabel = source?.key === "live_bridge"
        ? "Live status connected"
        : "Sanitized status loaded";
    const paperBalance = capital.equity_gbp ?? capital.current_balance_gbp ?? capital.starting_balance_gbp;
    setText("[data-mode-label]", `${dashboardText(status.mode).toUpperCase()} MODE`);
    setText("[data-capital-label]", `${formatCapitalMoney(paperBalance, capital)} paper account`);
    setText(
        "[data-live-capital-label]",
        capital.live_capital_enabled ? "Live capital enabled" : "OK - live capital off"
    );
    setText("[data-snapshot-meta]", `Snapshot ${generatedAt} · schema ${status.schema_version} · ${sourceLabel}`);

    const banner = dashboardQuery("[data-status-banner]");
    if (banner) {
        banner.classList.remove("snapshot-error");
        banner.innerHTML = `
            <span>${status.d0_shell?.status === "frozen" ? "D0 shell frozen" : "D0 shell unknown"}</span>
            <span>${d1Snapshot.public_safe ? "Dashboard status loaded" : "Dashboard metadata missing"}</span>
            <span>${liveBridge.status === "read_only_ready" ? bridgeSourceLabel : "Live status pending"}</span>
            <span>${status.boundary || "Read-only dashboard snapshot."}</span>
        `;
    }
}

function renderDashboardSafetyStrip(status, viewModels = {}) {
    const strip = viewModels.safety_strip_model || buildDashboardSafetyStripModel(status, viewModels);
    const target = dashboardQuery("[data-dashboard-safety-strip]");
    setText("[data-mode-label]", strip.mode_label);
    setText("[data-capital-label]", strip.capital_label);
    setText("[data-live-capital-label]", strip.live_capital_label);
    if (!target) return;
    ["online", "pending", "degraded", "blocked"].forEach((name) => target.classList.remove(name));
    target.classList.add(statusClass(strip.tone));
    target.innerHTML = `
        <div class="dashboard-safety-strip-main">
            <p class="label">Safety status</p>
            <h2>${htmlText(strip.headline)}</h2>
            <p>${htmlText(strip.summary)}</p>
        </div>
        <div class="dashboard-safety-strip-badges">
            <span class="inline-badge ${statusClass(strip.mode_label)}" data-mode-label>${htmlText(strip.mode_label)}</span>
            <span class="inline-badge ${statusClass(strip.write_authority ? "blocked" : "online")}" data-capital-label>${htmlText(strip.capital_label)}</span>
            <span class="inline-badge ${statusClass(strip.live_capital_enabled ? "blocked" : "online")}" data-live-capital-label>${htmlText(strip.live_capital_label)}</span>
            ${renderInlineBadge(strip.authority_label, strip.authority_tone)}
            ${renderInlineBadge(strip.read_only_label, strip.read_only_label === "OK - read-only" ? "online" : "blocked")}
        </div>
        <div class="dashboard-safety-strip-authority">
            <strong>${htmlText(strip.authority_status)}</strong>
            <span>${htmlText(strip.authority_blocker_label)}</span>
            <small>${htmlText(strip.authority_next_action)}</small>
        </div>
        <div class="info-hover safety-strip-info">
            <button class="info-button" type="button" aria-label="About Safety Status">i</button>
            <div class="info-card section-explainer" role="tooltip" data-section-explainer="status_safety" data-tooltip-contract="compact">
                <strong>Safety Status</strong>
                <p>One place for paper mode, capital, and order authority.</p>
                <dl class="explainer-grid compact">
                    <div><dt>Shows</dt><dd>${htmlText(strip.mode_label)} · ${htmlText(strip.live_capital_label)}</dd></div>
                    <div><dt>Paper authority</dt><dd>${htmlText(strip.authority_status)}</dd></div>
                    <div><dt>Watch</dt><dd>${htmlText(strip.authority_flag_count)} active authority flags.</dd></div>
                    <div><dt>Limits</dt><dd>Readout only; this page cannot place orders.</dd></div>
                </dl>
            </div>
        </div>
    `;
}

function renderPriorityCard(label, value, body, meta, tone = "neutral") {
    return `
        <article class="priority-card ${statusClass(tone)}">
            <span>${htmlText(label)}</span>
            <strong>${htmlText(value)}</strong>
            <p>${htmlText(body)}</p>
            <small>${htmlText(meta)}</small>
        </article>
    `;
}

function compactItems(items, limit = 5) {
    const list = asArray(items).filter(Boolean);
    const visible = list.slice(0, limit);
    const overflow = list.length - visible.length;
    return overflow > 0 ? [...visible, `+${overflow} more`] : visible;
}

function renderMissionTags(items, emptyText = "None recorded", limit = 5) {
    return renderTagList(compactItems(items, limit), emptyText);
}

function phase4StrategyStatus(status, mission = {}) {
    return status.phase4_strategy || mission.phase4_strategy || {};
}

function phase4ApprovalTone(phase4) {
    const approvalState = phase4.approval_event_status || phase4.approval_event?.approval_state;
    if (phase4.phase4_certification_allowed || approvalState === "approved") return "online";
    if (approvalState === "amendments_required" || approvalState === "missing") return "blocked";
    return "pending";
}

function phase4ApprovedShadowCount(phase4) {
    const toggles = phase4.strategy_toggles || {};
    return phase4.approved_shadow_strategy_toggle_count
        ?? toggles.approved_shadow_toggle_count
        ?? 0;
}

function shortFingerprint(value) {
    if (!value) return "not exported";
    return `${String(value).slice(0, 12)}...`;
}

function fallbackMissionControl(status, source) {
    const watching = asArray(status.watching);
    const sourceCounts = countBy(watching, "status");
    const pipelineSummary = asArray(status.source_pipeline_summary);
    const configuredSources = watching
        .filter((item) => item.credential_status === "configured")
        .map((item) => item.source_name || item.source_key);
    const connectedSources = Array.from(new Set([
        ...configuredSources,
        ...watching.filter((item) => item.status === "online").map((item) => item.source_name || item.source_key)
    ]));
    const missingCredentialCount = pipelineSummary.reduce(
        (total, pipeline) => total + Number(pipeline.missing_credential_count || 0),
        0
    );
    const cognition = status.cognition || {};
    const tradeLayer = status.trade_layer || {};
    const capital = status.capital || {};
    const philosophy = status.decision_philosophy || {};
    const durable = status.durable_ingestion || {};
    const preferenceMcp = status.preference_mcp || {};
    const quantumOracle = status.quantum_oracle || {};
    const providerReadiness = quantumOracle.provider_readiness || {};
    const providerByKey = (key) => asArray(providerReadiness.providers).find((provider) => provider.key === key) || {};
    const qctrl = providerReadiness.qctrl_readiness || {};
    const localSimulator = quantumOracle.local_simulator || {};
    const scheduler = quantumOracle.scheduler_dry_run || {};
    const signalReview = status.phase5_signal_review || {};
    const paperTradeDrill = status.phase5_paper_trade_drill || {};
    const phase5Certification = status.phase5_certification || {};
    const phase5Phase6Handoff = status.phase5_phase6_handoff || {};
    const systemMap = status.phase5_system_map || {};
    const phase6LearningLoop = status.phase6_learning_loop || {};
    const phase6Certification = status.phase6_certification || {};
    const phase7DemoProof = status.phase7_demo_proof || {};
    const candidates = asArray(tradeLayer.candidates);
    const observedSignals = asArray(tradeLayer.watching);
    const blockedTrades = asArray(tradeLayer.blocked);
    const openPositions = asArray(capital.open_positions);
    const totalPnl = Number(capital.realized_pnl_gbp || 0) + Number(capital.unrealized_pnl_gbp || 0);
    const phase4 = phase4StrategyStatus(status);
    return {
        status: "read_only_mission_control",
        source: source?.key || "dashboard_fallback",
        headline: `${sourceCounts.online || 0}/${watching.length} sources online; ${asArray(cognition.hypotheses).length} hypotheses; ${candidates.length} candidates; ${openPositions.length} open positions; live capital ${capital.live_capital_enabled ? "enabled" : "disabled"}.`,
        data_sources: {
            total_count: watching.length,
            online_count: sourceCounts.online || 0,
            degraded_count: sourceCounts.degraded || 0,
            pending_count: sourceCounts.pending || 0,
            missing_credential_count: missingCredentialCount,
            durable_replay_status: durable.replay_status || "unknown",
            durable_replayed_source_count: durable.replayed_source_count || 0,
            durable_expected_source_count: durable.expected_source_count || 0,
            preference_mcp_status: preferenceMcp.status || "not_exported",
            preference_mcp_identity_status: preferenceMcp.identity_status || "not_verified",
            preference_mcp_quota_status: preferenceMcp.quota_status || "unknown",
            preference_mcp_catalog_status: preferenceMcp.catalog_status || "not_run",
            preference_mcp_domain_pack_count: preferenceMcp.approved_domain_pack_count || 0,
            preference_mcp_provenance_status: preferenceMcp.provenance_status || "not_run",
            preference_mcp_shadow_context_status: preferenceMcp.shadow_context_status || "not_run",
            preference_mcp_degraded_reason: preferenceMcp.degraded_reason || null,
            logged_in_count: configuredSources.length,
            logged_in_sources: configuredSources,
            connected_sources: connectedSources,
            boundary: "Configured and connected sources are observation inputs only; they cannot create orders. Supplemental data planes are observation inputs only."
        },
        durable_spine: {
            status: durable.status || "unknown",
            service_status: durable.service_status || "unknown",
            contract_status: durable.contract_status || "unknown",
            replay_status: durable.replay_status || "unknown",
            observation_count: durable.observation_count || 0,
            replayed_source_count: durable.replayed_source_count || 0,
            expected_source_count: durable.expected_source_count || 0,
            missing_source_count: durable.missing_source_count || 0,
            latest_observed_at: durable.latest_observed_at || null,
            next_step: durable.next_step || "Verify durable replay readiness.",
            write_authority: false,
            signal_authority: false,
            order_authority: false,
            boundary: durable.boundary || "Read-only durable ingestion readiness. It cannot create signals, candidates, orders, or broker writes."
        },
        trading_philosophy: {
            status: philosophy.status || "pending",
            summary: philosophy.trading_philosophy || "Qadam generates hypotheses from private priors, but live evidence and gates decide what can advance.",
            decision_chain: philosophy.decision_chain || [],
            private_prior_count: philosophy.foundational_prior_count || 0,
            current_self_directive: [
                "Use worldview as private prior.",
                "Require live-source corroboration.",
                "Compress source noise locally.",
                "Challenge with Strategy Lead.",
                "Keep paper orders blocked until gates pass."
            ],
            boundary: philosophy.boundary || "Worldview is context only, not evidence."
        },
        system_stack: {
            coo: findModule(status, "event_log")?.status || "local_only",
            data_spine: watching.length ? "online" : "pending",
            durable_spine: durable.contract_status || "unknown",
            local_llm: findModule(status, "research_analyst")?.status || "pending",
            frontier_llm: findModule(status, "strategy_lead")?.status || "pending",
            quant_oracle: findModule(status, "head_of_quant")?.status || "deferred",
            quant_oracle_backend: status.quantum_oracle?.latest_backend || "classical_fallback",
            quant_oracle_mode: status.quantum_oracle?.latest_local_simulation_mode || "not_run",
            quant_oracle_recommendation: status.quantum_oracle?.latest_recommendation || "not_run",
            risk_gate: status.risk_agent?.status || "pending",
            preference_mcp: preferenceMcp.status || "not_configured",
            phase5_layer_b: status.phase5_layer_b_readiness?.status || "not_run",
            phase5_kill_switch: status.phase5_kill_switch_ledger?.status || "not_run",
            phase5_execution_adapter: status.phase5_execution_adapter_status?.status || "not_run",
            phase5_paper_order_staging: status.phase5_paper_order_staging_gate?.status || "not_run",
            phase5_alpaca_paper_dry_run: status.phase5_alpaca_paper_dry_run?.status || "not_run",
            phase5_paper_submit_enablement: status.phase5_paper_submit_enablement_gate?.status || "not_run",
            phase5_prediction_market_adapter: status.phase5_prediction_market_adapter?.status || "not_run",
            phase5_telegram_notifier: status.phase5_telegram_notifier?.status || "not_run",
            phase5_position_monitor: status.phase5_position_monitor?.status || "not_run",
            phase5_signal_review: signalReview.status || "not_run",
            phase5_paper_trade_drill: paperTradeDrill.status || "not_run",
            phase5_certification: phase5Certification.status || "not_run",
            phase5_phase6_handoff: phase5Phase6Handoff.status || "not_run",
            phase5_system_map: systemMap.status || "not_run",
            phase6_learning_loop: phase6LearningLoop.status || "not_run",
            phase7_demo_proof: phase7DemoProof.status || "not_run",
            paper_account: capital.mirror_status || "pending",
            telegram: status.communications?.telegram?.status || "pending",
            boundary: "APIs, models, and quantum checks can inform the chain; only gates can advance state."
        },
        phase3_readiness: {
            schema_version: 1,
            phase: "Q3",
            status: "provider_scheduler_readiness",
            readiness_scope: "provider_scheduler_readiness",
            execution_readiness: "not_execution_ready",
            public_safe: true,
            provider_readiness_status: providerReadiness.status || "unknown",
            provider_count: providerReadiness.provider_count || 0,
            expected_provider_count: providerReadiness.expected_provider_count || 0,
            configured_provider_count: providerReadiness.configured_count || 0,
            missing_secret_count: providerReadiness.missing_secret_count || 0,
            missing_optional_package_count: providerReadiness.missing_optional_package_count || 0,
            qctrl_configured: Boolean(providerReadiness.qctrl_configured),
            qctrl_status: qctrl.status || "unknown",
            qctrl_live_probe_enabled: Boolean(qctrl.live_probe_enabled),
            qctrl_provider_call_count: qctrl.provider_call_count || 0,
            qctrl_optimization_job_submitted: Boolean(qctrl.optimization_job_submitted),
            qiskit_available: Boolean(quantumOracle.qiskit_available || localSimulator.qiskit_available),
            qiskit_aer_available: Boolean(quantumOracle.qiskit_aer_available || localSimulator.qiskit_aer_available),
            local_simulator_status: localSimulator.status || "unknown",
            local_simulator_backend: localSimulator.selected_backend || quantumOracle.latest_backend || "classical_fallback",
            local_simulator_mode: quantumOracle.latest_local_simulation_mode || "not_run",
            ibm_quantum_status: providerByKey("ibm_quantum").status || "unknown",
            aws_braket_status: providerByKey("aws_braket").status || "unknown",
            scheduler_status: scheduler.status || "unknown",
            scheduler_due: Boolean(scheduler.due),
            scheduler_enabled: Boolean(scheduler.scheduler_enabled),
            autonomous_scheduler_enabled: Boolean(scheduler.autonomous_scheduler_enabled),
            scheduler_would_queue_job_count: scheduler.would_queue_job_count || 0,
            scheduler_jobs_queued_count: scheduler.jobs_queued_count || 0,
            scheduler_jobs_submitted_count: scheduler.jobs_submitted_count || 0,
            latest_recommendation: quantumOracle.latest_recommendation || "not_run",
            latest_output_route_type: quantumOracle.latest_output_route_type || "not_run",
            latest_output_storage_type: quantumOracle.latest_output_storage_type || "not_run",
            latest_output_routing_status: quantumOracle.latest_output_routing_status || "not_run",
            latest_oracle_created_at: quantumOracle.latest_created_at || null,
            next_due_at: quantumOracle.next_due_at || scheduler.next_due_at || null,
            hardware_submission_allowed_count: quantumOracle.hardware_submission_allowed_count || 0,
            hardware_submitted_count: quantumOracle.hardware_submitted_count || 0,
            hardware_scheduler_enabled_count: quantumOracle.hardware_scheduler_enabled_count || 0,
            execution_allowed_count: quantumOracle.execution_allowed_count || 0,
            paper_order_allowed_count: quantumOracle.paper_order_allowed_count || 0,
            trade_candidate_created_count: quantumOracle.trade_candidate_created_count || 0,
            secret_value_exposed_count: providerReadiness.secret_value_exposed_count || 0,
            raw_response_exposed_count: providerReadiness.raw_response_exposed_count || 0,
            local_absolute_path_exposed_count: 0,
            cloud_job_identifier_exposed_count: 0,
            boundary: "Provider and scheduler readiness is status only, not execution readiness. It exposes sanitized counters only; no secret values, raw provider responses, local absolute paths, provider payloads, or unsanitized cloud job identifiers."
        },
        phase4_strategy: {
            phase: phase4.phase || "Q4",
            stage: phase4.stage || "Q4-11",
            stage_status: phase4.stage_status || "not_exported",
            audit_completion_state: phase4.audit_completion_state || {},
            strategy_document_status: phase4.strategy_document_status || "missing",
            approval_event_status: phase4.approval_event_status || "missing",
            approval_logged: phase4.approval_event?.approval_logged === true,
            toggle_count: phase4.toggle_count || phase4.strategy_toggles?.toggle_count || 0,
            approved_shadow_strategy_toggle_count: phase4ApprovedShadowCount(phase4),
            phase4_certification_allowed: Boolean(phase4.phase4_certification_allowed),
            trade_candidate_count: phase4.trade_candidate_count || 0,
            execution_allowed_count: phase4.execution_allowed_count || 0,
            paper_order_allowed_count: phase4.paper_order_allowed_count || 0,
            broker_write_allowed_count: phase4.broker_write_allowed_count || 0,
            live_capital_enabled_count: phase4.live_capital_enabled_count || 0,
            boundary: phase4.boundary || phase4.no_execution_boundary || "Phase 4 strategy visibility is governance-only and non-executable."
        },
        phase5_layer_b: {
            phase: status.phase5_layer_b_readiness?.phase || "Q5",
            layer: status.phase5_layer_b_readiness?.layer || "Layer B",
            stage: status.phase5_layer_b_readiness?.stage || "P5-PRE",
            status: status.phase5_layer_b_readiness?.status || "not_run",
            implementation_plan_allowed: Boolean(status.phase5_layer_b_readiness?.phase5_layer_b_implementation_plan_allowed),
            implementation_allowed: Boolean(status.phase5_layer_b_readiness?.phase5_layer_b_implementation_allowed),
            orchestration_start_allowed: Boolean(status.phase5_layer_b_readiness?.phase5_orchestration_start_allowed),
            readiness_blocker_count: status.phase5_layer_b_readiness?.readiness_blocker_count || 0,
            nonapproval_blocker_count: status.phase5_layer_b_readiness?.nonapproval_blocker_count || 0,
            only_explicit_approval_blocks_plan: Boolean(status.phase5_layer_b_readiness?.only_explicit_approval_blocks_phase5_plan),
            scope_count: status.phase5_layer_b_readiness?.phase5_layer_b_scope_count || 0,
            kill_switch_status: status.phase5_kill_switch_ledger?.status || "not_run",
            kill_switch_count: status.phase5_kill_switch_ledger?.switch_count || 0,
            kill_switch_active_count: status.phase5_kill_switch_ledger?.active_switch_count || 0,
            kill_switch_blocking_count: status.phase5_kill_switch_ledger?.blocking_switch_count || 0,
            kill_switch_event_log_written: Boolean(status.phase5_kill_switch_ledger?.event_log_written),
            execution_adapter_status: status.phase5_execution_adapter_status?.status || "not_run",
            execution_adapter_count: status.phase5_execution_adapter_status?.adapter_status_count || 0,
            execution_adapter_read_allowed_count: status.phase5_execution_adapter_status?.read_allowed_count || 0,
            execution_adapter_staging_allowed_count: status.phase5_execution_adapter_status?.downstream_staging_allowed_count || 0,
            paper_order_staging_status: status.phase5_paper_order_staging_gate?.status || "not_run",
            paper_order_staging_record_count: status.phase5_paper_order_staging_gate?.staging_record_count || 0,
            paper_order_staged_count: status.phase5_paper_order_staging_gate?.staged_order_count || 0,
            paper_order_staging_blocked_count: status.phase5_paper_order_staging_gate?.blocked_count || 0,
            paper_order_staging_event_log_written: Boolean(status.phase5_paper_order_staging_gate?.event_log_written),
            alpaca_paper_dry_run_status: status.phase5_alpaca_paper_dry_run?.status || "not_run",
            alpaca_paper_dry_run_record_count: status.phase5_alpaca_paper_dry_run?.dry_run_record_count || 0,
            alpaca_paper_dry_run_request_preview_count: status.phase5_alpaca_paper_dry_run?.request_preview_count || 0,
            alpaca_paper_dry_run_receipt_count: status.phase5_alpaca_paper_dry_run?.dry_run_receipt_count || 0,
            alpaca_paper_dry_run_blocked_count: status.phase5_alpaca_paper_dry_run?.blocked_count || 0,
            alpaca_paper_dry_run_event_log_written: Boolean(status.phase5_alpaca_paper_dry_run?.event_log_written),
            alpaca_paper_dry_run_broker_post_called: Boolean(status.phase5_alpaca_paper_dry_run?.broker_post_called),
            paper_submit_enablement_status: status.phase5_paper_submit_enablement_gate?.status || "not_run",
            paper_submit_enablement_record_count: status.phase5_paper_submit_enablement_gate?.submit_enablement_record_count || 0,
            paper_submit_path_available_count: status.phase5_paper_trade_drill?.paper_submit_path_available_count || status.phase5_paper_submit_enablement_gate?.submit_path_available_count || 0,
            paper_submit_approval_state: status.phase5_paper_submit_enablement_gate?.paper_submit_approval_state || "missing",
            paper_submit_approval_present: Boolean(status.phase5_paper_submit_enablement_gate?.paper_submit_approval_present),
            paper_submit_event_log_written: Boolean(status.phase5_paper_submit_enablement_gate?.event_log_written),
            paper_submit_broker_post_called: Boolean(status.phase5_paper_submit_enablement_gate?.broker_post_called),
            prediction_market_adapter_status: status.phase5_prediction_market_adapter?.status || "not_run",
            prediction_market_route_count: status.phase5_prediction_market_adapter?.prediction_market_route_count || 0,
            prediction_market_context_count: status.phase5_prediction_market_adapter?.prediction_market_context_count || 0,
            prediction_market_read_only_route_count: status.phase5_prediction_market_adapter?.read_only_route_count || 0,
            prediction_market_live_blocked_route_count: status.phase5_prediction_market_adapter?.live_blocked_count || 0,
            prediction_market_write_allowed_count: status.phase5_prediction_market_adapter?.prediction_market_write_allowed_count || 0,
            prediction_market_spend_allowed_count: status.phase5_prediction_market_adapter?.prediction_market_spend_allowed_count || 0,
            prediction_market_preference_provenance_status: status.phase5_prediction_market_adapter?.preference_provenance_status || "not_run",
            prediction_market_preference_source_quorum_credit_allowed: Boolean(status.phase5_prediction_market_adapter?.preference_source_quorum_credit_allowed),
            prediction_market_event_log_written: Boolean(status.phase5_prediction_market_adapter?.event_log_written),
            telegram_notifier_status: status.phase5_telegram_notifier?.status || "not_run",
            telegram_notifier_alert_type_count: status.phase5_telegram_notifier?.alert_type_count || 0,
            telegram_notifier_eligible_alert_count: status.phase5_telegram_notifier?.eligible_alert_count || 0,
            telegram_notifier_queued_count: status.phase5_telegram_notifier?.queued_dry_run_alert_count || 0,
            telegram_notifier_outbox_written_count: status.phase5_telegram_notifier?.outbox_message_written_count || 0,
            telegram_notifier_suppressed_count: status.phase5_telegram_notifier?.suppressed_alert_count || 0,
            telegram_notifier_send_gate: status.phase5_telegram_notifier?.telegram_send_gate || "not_run",
            telegram_notifier_mode: status.phase5_telegram_notifier?.telegram_mode || "not_run",
            telegram_notifier_command_path_enabled_count: status.phase5_telegram_notifier?.telegram_command_path_enabled_count || 0,
            telegram_notifier_live_send_allowed_count: status.phase5_telegram_notifier?.live_send_allowed_count || 0,
            telegram_notifier_event_log_written: Boolean(status.phase5_telegram_notifier?.event_log_written),
            position_monitor_status: status.phase5_position_monitor?.status || "not_run",
            position_monitor_record_count: status.phase5_position_monitor?.monitor_record_count || 0,
            position_monitor_position_record_count: status.phase5_position_monitor?.position_record_count || 0,
            position_monitor_closed_trade_summary_count: status.phase5_position_monitor?.closed_trade_summary_count || 0,
            position_monitor_submitted_order_count: status.phase5_position_monitor?.submitted_order_count || 0,
            position_monitor_mirrored_order_count: status.phase5_position_monitor?.mirrored_order_count || 0,
            position_monitor_open_position_count: status.phase5_position_monitor?.open_position_count || 0,
            position_monitor_closed_trade_count: status.phase5_position_monitor?.closed_trade_count || 0,
            position_monitor_failed_reconciliation_count: status.phase5_position_monitor?.failed_reconciliation_count || 0,
            position_monitor_event_log_written: Boolean(status.phase5_position_monitor?.event_log_written),
            position_monitor_write_authority_count: status.phase5_position_monitor?.position_monitor_write_authority_count || 0,
            position_monitor_close_allowed_count: status.phase5_position_monitor?.position_close_allowed_count || 0,
            position_monitor_resize_allowed_count: status.phase5_position_monitor?.position_resize_allowed_count || 0,
            position_monitor_cancel_allowed_count: status.phase5_position_monitor?.order_cancel_allowed_count || 0,
            signal_review_status: signalReview.status || "not_run",
            signal_review_record_count: signalReview.signal_review_record_count || 0,
            signal_review_decision_chain_count: signalReview.decision_chain_count || 0,
            signal_review_governance_comment_event_count: signalReview.governance_comment_event_count || 0,
            signal_review_kill_switch_action_event_count: signalReview.kill_switch_action_event_count || 0,
            signal_review_backend_truth_displayed_count: signalReview.backend_truth_displayed_count || 0,
            signal_review_ui_inferred_readiness_count: signalReview.ui_inferred_readiness_count || 0,
            signal_review_event_log_written: Boolean(signalReview.event_log_written),
            signal_review_trade_approval_control_count: signalReview.trade_approval_control_enabled_count || 0,
            signal_review_order_place_control_count: signalReview.order_place_control_enabled_count || 0,
            signal_review_position_close_control_count: signalReview.position_close_control_enabled_count || 0,
            signal_review_position_resize_control_count: signalReview.position_resize_control_enabled_count || 0,
            signal_review_order_cancel_control_count: signalReview.order_cancel_control_enabled_count || 0,
            signal_review_broker_write_allowed_count: signalReview.broker_write_allowed_count || 0,
            signal_review_prediction_market_write_allowed_count: signalReview.prediction_market_write_allowed_count || 0,
            signal_review_live_capital_enabled_count: signalReview.live_capital_enabled_count || 0,
            paper_trade_drill_status: paperTradeDrill.status || "not_run",
            paper_trade_drill_state: paperTradeDrill.paper_trade_drill_state || "not_run",
            paper_trade_drill_step_count: paperTradeDrill.step_count || 0,
            paper_trade_drill_blocker_count: paperTradeDrill.blocker_count || 0,
            paper_trade_drill_complete: Boolean(paperTradeDrill.paper_trade_drill_complete),
            paper_trade_drill_exit_gate_passed: Boolean(paperTradeDrill.phase5_paper_trade_drill_exit_gate_passed),
            paper_trade_drill_implementation_ready: Boolean(paperTradeDrill.phase5_paper_trade_drill_implementation_ready),
            paper_trade_drill_submit_approval_present: Boolean(paperTradeDrill.paper_submit_approval_present),
            paper_trade_drill_submit_path_available_count: paperTradeDrill.paper_submit_path_available_count || 0,
            paper_trade_drill_submitted_order_count: paperTradeDrill.submitted_paper_order_count || 0,
            paper_trade_drill_open_position_count: paperTradeDrill.open_position_count || 0,
            paper_trade_drill_closed_trade_count: paperTradeDrill.closed_trade_count || 0,
            paper_trade_drill_postmortem_due_count: paperTradeDrill.postmortem_due_count || 0,
            paper_trade_drill_broker_post_called_count: paperTradeDrill.broker_post_called_count || 0,
            paper_trade_drill_live_capital_enabled_count: paperTradeDrill.live_capital_enabled_count || 0,
            certification_status: phase5Certification.status || "not_run",
            certification_stage_status: phase5Certification.stage_status || "not_run",
            certification_phase5_certified: Boolean(phase5Certification.phase5_certified),
            certification_phase5_exit_gate: Boolean(phase5Certification.phase5_exit_gate),
            certification_phase6_handoff_allowed: Boolean(phase5Certification.phase6_handoff_allowed),
            certification_phase7_planning_allowed: Boolean(phase5Certification.phase7_planning_allowed),
            certification_phase7_proof_credit_allowed: Boolean(phase5Certification.phase7_proof_credit_allowed),
            certification_input_gate_count: phase5Certification.input_gate_count || 0,
            certification_input_gate_passed_count: phase5Certification.input_gate_passed_count || 0,
            certification_input_gate_blocked_count: phase5Certification.input_gate_blocked_count || 0,
            certification_blocker_count: phase5Certification.certification_blocker_count || 0,
            certification_paper_trade_drill_complete: Boolean(phase5Certification.paper_trade_drill_complete),
            certification_paper_trade_drill_exit_gate_passed: Boolean(phase5Certification.paper_trade_drill_exit_gate_passed),
            certification_submitted_paper_order_count: phase5Certification.submitted_paper_order_count || 0,
            certification_open_position_count: phase5Certification.open_position_count || 0,
            certification_closed_trade_count: phase5Certification.closed_trade_count || 0,
            certification_live_capital_enabled_count: phase5Certification.live_capital_enabled_count || 0,
            phase6_handoff_status: phase5Phase6Handoff.status || "not_run",
            phase6_handoff_state: phase5Phase6Handoff.handoff_state || "not_run",
            phase6_handoff_blocker_count: phase5Phase6Handoff.blocker_count || 0,
            phase6_handoff_event_log_written: Boolean(phase5Phase6Handoff.event_log_written),
            phase6_learning_loop_plan_allowed: Boolean(phase5Phase6Handoff.phase6_learning_loop_plan_allowed),
            phase6_learning_loop_implementation_allowed: Boolean(phase5Phase6Handoff.phase6_learning_loop_implementation_allowed),
            phase6_learning_write_allowed: Boolean(phase5Phase6Handoff.phase6_learning_write_allowed),
            phase6_knowledge_graph_write_allowed: Boolean(phase5Phase6Handoff.phase6_knowledge_graph_write_allowed),
            phase6_required_module_count: phase5Phase6Handoff.phase6_required_module_count || 0,
            phase6_handoff_closed_trade_count: phase5Phase6Handoff.closed_trade_count || 0,
            phase6_handoff_postmortem_due_count: phase5Phase6Handoff.postmortem_due_count || 0,
            phase6_handoff_phase7_proof_credit_allowed: Boolean(phase5Phase6Handoff.phase7_proof_credit_allowed),
            phase6_handoff_live_capital_enabled_count: phase5Phase6Handoff.live_capital_enabled_count || 0,
            phase6_handoff_recommended_next_stage: phase5Phase6Handoff.recommended_next_stage || "Q6-0 Phase 6 re-entry and learning-loop implementation plan",
            system_map_status: systemMap.status || "not_run",
            system_map_node_count: systemMap.node_count || 0,
            system_map_lane_count: systemMap.lane_count || 0,
            system_map_layer_b_node_count: systemMap.layer_b_node_count || 0,
            system_map_backend_parity_error_count: systemMap.backend_parity_error_count || 0,
            system_map_unsafe_control_count: systemMap.unsafe_control_count || 0,
            system_map_event_log_written: Boolean(systemMap.event_log_written),
            system_map_dashboard_claims_trading_now: Boolean(
                systemMap.guardrails?.dashboard_claims_trading_now
            ),
            boundary: status.phase5_layer_b_readiness?.boundary || "Phase 5 readiness is planning-only until Q4-12 certifies."
        },
        phase6_learning_loop: {
            phase: phase6LearningLoop.phase || "Q6",
            stage: phase6LearningLoop.stage || "Q6-16",
            status: phase6LearningLoop.status || "not_run",
            visibility_state: phase6LearningLoop.visibility_state || "not_visible",
            learning_state: phase6LearningLoop.learning_state || "not_run",
            backend_derived: Boolean(phase6LearningLoop.backend_derived),
            display_derived_from_backend: Boolean(phase6LearningLoop.display_derived_from_backend),
            ui_inferred_readiness_count: phase6LearningLoop.ui_inferred_readiness_count || 0,
            backend_parity_error_count: phase6LearningLoop.backend_parity_error_count || 0,
            postmortem_due_count: phase6LearningLoop.postmortem_due_count || 0,
            postmortem_resolved_count: phase6LearningLoop.postmortem_resolved_count || 0,
            approval_state: phase6LearningLoop.approval_state || "not_requested",
            staged_graph_entry_count: phase6LearningLoop.staged_graph_entry_count || 0,
            knowledge_graph_read_result_count: phase6LearningLoop.knowledge_graph_read_result_count || 0,
            model_weight_proposal_count: phase6LearningLoop.model_weight_proposal_count || 0,
            trust_score_proposal_count: phase6LearningLoop.trust_score_proposal_count || 0,
            shadow_replay_variant_count: phase6LearningLoop.shadow_replay_variant_count || 0,
            architect_recommendation_count: phase6LearningLoop.architect_recommendation_count || 0,
            architect_blocked_recommendation_count: phase6LearningLoop.architect_blocked_recommendation_count || 0,
            blocked_authority_count: phase6LearningLoop.blocked_authority_count || 0,
            phase6_learning_write_allowed: Boolean(phase6LearningLoop.phase6_learning_write_allowed),
            phase6_knowledge_graph_write_allowed: Boolean(phase6LearningLoop.phase6_knowledge_graph_write_allowed),
            phase6_model_weight_update_allowed: Boolean(phase6LearningLoop.phase6_model_weight_update_allowed),
            phase6_trust_score_update_allowed: Boolean(phase6LearningLoop.phase6_trust_score_update_allowed),
            phase6_architect_policy_mutation_allowed: Boolean(phase6LearningLoop.phase6_architect_policy_mutation_allowed),
            phase7_proof_credit_allowed: Boolean(phase6LearningLoop.phase7_proof_credit_allowed),
            live_capital_enabled: Boolean(phase6LearningLoop.live_capital_enabled),
            unsafe_write_counter_total: phase6LearningLoop.unsafe_write_counter_total || 0,
            raw_payload_exposed_count: phase6LearningLoop.raw_payload_exposed_count || 0,
            local_path_exposed_count: phase6LearningLoop.local_path_exposed_count || 0,
            secret_ref_exposed_count: phase6LearningLoop.secret_ref_exposed_count || 0,
            broker_identifier_exposed_count: phase6LearningLoop.broker_identifier_exposed_count || 0,
            boundary: phase6LearningLoop.boundary || "Phase 6 Learning Loop visibility is backend-derived and non-executable."
        },
        phase6_certification: {
            phase: phase6Certification.phase || "Q6",
            stage: phase6Certification.stage || "Q6-17",
            status: phase6Certification.status || "not_run",
            stage_status: phase6Certification.stage_status || "not_run",
            certification_state: phase6Certification.certification_state || "not_run",
            phase6_certified: Boolean(phase6Certification.phase6_certified),
            phase6_exit_gate: Boolean(phase6Certification.phase6_exit_gate),
            phase7_demo_proof_planning_allowed: Boolean(
                phase6Certification.phase7_demo_proof_planning_allowed
            ),
            phase7_proof_credit_allowed: Boolean(phase6Certification.phase7_proof_credit_allowed),
            phase5_test_trades_count_for_phase7: Boolean(
                phase6Certification.phase5_test_trades_count_for_phase7
            ),
            input_gate_passed_count: phase6Certification.input_gate_passed_count || 0,
            input_gate_blocked_count: phase6Certification.input_gate_blocked_count || 0,
            certification_blocker_count: phase6Certification.certification_blocker_count || 0,
            postmortem_due_count: phase6Certification.postmortem_due_count || 0,
            unresolved_postmortem_count: phase6Certification.unresolved_postmortem_count || 0,
            approval_state: phase6Certification.approval_state || "not_requested",
            pending_review_action_count: phase6Certification.pending_review_action_count || 0,
            learning_actions_review_satisfied: Boolean(
                phase6Certification.learning_actions_review_satisfied
            ),
            knowledge_graph_requirement_satisfied: Boolean(
                phase6Certification.knowledge_graph_requirement_satisfied
            ),
            unsafe_write_counter_total: phase6Certification.unsafe_write_counter_total || 0,
            live_capital_enabled: Boolean(phase6Certification.live_capital_enabled),
            boundary: phase6Certification.boundary || "Q6-17 certification cannot approve learning or enable live capital."
        },
        phase7_demo_proof: {
            phase: phase7DemoProof.phase || "Q7",
            stage: phase7DemoProof.stage || "Q7-15",
            status: phase7DemoProof.status || "not_run",
            stage_status: phase7DemoProof.stage_status || "not_run",
            visibility_state: phase7DemoProof.visibility_state || "not_visible",
            proof_state: phase7DemoProof.proof_state || "not_run",
            backend_derived: Boolean(phase7DemoProof.backend_derived),
            display_derived_from_backend: Boolean(phase7DemoProof.display_derived_from_backend),
            dashboard_uses_backend_status: Boolean(phase7DemoProof.dashboard_uses_backend_status),
            ui_inferred_readiness_count: phase7DemoProof.ui_inferred_readiness_count || 0,
            source_artifact_count: phase7DemoProof.source_artifact_count || 0,
            source_missing_count: phase7DemoProof.source_missing_count || 0,
            source_validation_error_count: phase7DemoProof.source_validation_error_count || 0,
            phase7_harness_day_count: phase7DemoProof.phase7_harness_day_count || 30,
            completed_calendar_day_count: phase7DemoProof.completed_calendar_day_count || 0,
            phase7_30_day_run_complete: Boolean(phase7DemoProof.phase7_30_day_run_complete),
            proof_week_count: phase7DemoProof.proof_week_count || 0,
            current_proof_week_number: phase7DemoProof.current_proof_week_number || 0,
            weekly_proof_trade_target: phase7DemoProof.weekly_proof_trade_target || 3,
            qualified_setup_count: phase7DemoProof.qualified_setup_count || 0,
            eligible_setup_count: phase7DemoProof.eligible_setup_count || 0,
            missed_qualified_setup_count: phase7DemoProof.missed_qualified_setup_count || 0,
            submitted_paper_order_count: phase7DemoProof.submitted_paper_order_count || 0,
            broker_receipt_count: phase7DemoProof.broker_receipt_count || 0,
            mirrored_submitted_order_count: phase7DemoProof.mirrored_submitted_order_count || 0,
            open_position_count: phase7DemoProof.open_position_count || 0,
            closed_proof_trade_count: phase7DemoProof.closed_proof_trade_count || 0,
            postmortem_due_count: phase7DemoProof.postmortem_due_count || 0,
            expectancy_after_costs_gbp: phase7DemoProof.expectancy_after_costs_gbp,
            expectancy_after_costs_positive: Boolean(phase7DemoProof.expectancy_after_costs_positive),
            drawdown_state: phase7DemoProof.drawdown_state || "unknown",
            drawdown_within_cap: Boolean(phase7DemoProof.drawdown_within_cap),
            max_drawdown_fraction_observed: phase7DemoProof.max_drawdown_fraction_observed,
            new_proof_trades_frozen: Boolean(phase7DemoProof.new_proof_trades_frozen),
            override_count: phase7DemoProof.override_count || 0,
            sample_contaminated: Boolean(phase7DemoProof.sample_contaminated),
            complete_decision_chain_count: phase7DemoProof.complete_decision_chain_count || 0,
            missing_decision_chain_count: phase7DemoProof.missing_decision_chain_count || 0,
            maturity_state: phase7DemoProof.maturity_state || "no_sample",
            mature_benchmark: phase7DemoProof.mature_benchmark || 100,
            maturity_progress_fraction: phase7DemoProof.maturity_progress_fraction || 0,
            closed_trades_remaining_to_mature: phase7DemoProof.closed_trades_remaining_to_mature || 100,
            phase7_mature_benchmark_met: Boolean(phase7DemoProof.phase7_mature_benchmark_met),
            phase7_mature_status_blocked: Boolean(phase7DemoProof.phase7_mature_status_blocked),
            phase7_statistical_immaturity_hidden: Boolean(phase7DemoProof.phase7_statistical_immaturity_hidden),
            phase5_test_trades_count_for_phase7: Boolean(phase7DemoProof.phase5_test_trades_count_for_phase7),
            phase7_proof_credit_allowed: Boolean(phase7DemoProof.phase7_proof_credit_allowed),
            live_capital_enabled: Boolean(phase7DemoProof.live_capital_enabled),
            broker_post_called_count: phase7DemoProof.broker_post_called_count || 0,
            alpaca_post_called_count: phase7DemoProof.alpaca_post_called_count || 0,
            unsafe_write_counter_total: phase7DemoProof.unsafe_write_counter_total || 0,
            q7_16_weekly_review_pack_stage_allowed: Boolean(phase7DemoProof.q7_16_weekly_review_pack_stage_allowed),
            boundary: phase7DemoProof.boundary || "Paper growth trial visibility is backend-derived and non-executable."
        },
        thinking: {
            status: cognition.status || "pending",
            phase2_status: phase2Cycle.status || "not_run",
            phase2_mode: phase2Cycle.mode || "not_run",
            phase2_queued_packet_count: phase2Cycle.queued_packet_count || 0,
            phase2_shadow_signal_count: phase2Cycle.shadow_signal_count || 0,
            phase2_durable_replay_status: phase2Cycle.durable_replay_status || "not_requested",
            phase2_durable_replayed_source_count: phase2Cycle.durable_replay_replayed_source_count || 0,
            phase2_durable_missing_source_count: phase2Cycle.durable_replay_missing_source_count || 0,
            current_focus: cognition.current_focus || [],
            hypothesis_count: asArray(cognition.hypotheses).length,
            evidence_packet_count: asArray(cognition.evidence_packets).length,
            local_assessment_count: asArray(cognition.local_research_assessments).length,
            strategy_packet_count: asArray(cognition.strategy_lead_packets).length,
            signal_integrity_status: cognition.signal_integrity?.status || "pending",
            blocked_reasons: cognition.blocked_reasons || [],
            boundary: cognition.boundary || "Reasoning is research-only and cannot execute trades."
        },
        trade_intent: {
            state: candidates.length ? "candidate_review" : (observedSignals.length ? "observed_signal_review" : "no_trade_candidate"),
            summary: candidates.length
                ? `${candidates.length} candidate ideas are waiting behind risk and execution gates.`
                : (observedSignals.length ? `${observedSignals.length} observed signals are being watched, but none are orders.` : "No executable trade idea exists in the current dashboard status."),
            observed_signal_count: observedSignals.length,
            candidate_count: candidates.length,
            blocked_count: blockedTrades.length,
            top_candidates: candidates.slice(0, 5),
            blocked_trades: blockedTrades.slice(0, 5),
            execution_allowed_count: 0,
            paper_order_submitted_count: status.paper_submit_receipt?.paper_order_submitted_count || 0,
            broker_post_called_count: status.paper_submit_receipt?.broker_post_called_count || 0,
            boundary: tradeLayer.boundary || "Candidate is not order; no broker route exists."
        },
        portfolio: {
            account_scope: capital.account_scope || "first_release_gbp_100000_paper",
            broker: capital.broker || "paper_broker",
            connection_status: capital.connection_status || "pending",
            display_currency: capital.display_currency || capital.account_currency || "GBP",
            portfolio_value_source: capital.portfolio_value_source || "paper account mirror",
            mirror_freshness_label: capital.mirror_freshness_label || "freshness unknown",
            portfolio_reconciliation: capital.portfolio_reconciliation || {},
            current_balance_gbp: capital.current_balance_gbp || capital.starting_balance_gbp || 0,
            total_pnl_gbp: totalPnl,
            drawdown_pct: capital.drawdown_pct || 0,
            open_position_count: openPositions.length,
            order_count: asArray(capital.orders).length,
            closed_trade_count: asArray(capital.closed_trades).length,
            live_capital_enabled: Boolean(capital.live_capital_enabled),
            write_authority: Boolean(capital.write_authority),
            open_positions: openPositions,
            orders: asArray(capital.orders),
            boundary: capital.boundary || "Read-only paper account mirror."
        },
        safety: {
            live_capital_enabled: Boolean(capital.live_capital_enabled),
            broker_write_allowed: false,
            forbidden_action_count: asArray(status.forbidden_actions).length,
            hard_blocks: asArray(status.forbidden_actions).map((item) => item.action || item.key || "blocked action"),
            boundary: "Mission control is read-only. It cannot approve, place, modify, resize, close, or fund trades."
        }
    };
}

function renderMissionControl(status, source) {
    const mission = status.mission_control || fallbackMissionControl(status, source);
    const dataSources = mission.data_sources || {};
    const philosophy = mission.trading_philosophy || {};
    const stack = mission.system_stack || {};
    const phase3 = mission.phase3_readiness || {};
    const phase4 = phase4StrategyStatus(status, mission);
    const phase5 = mission.phase5_layer_b || status.phase5_layer_b_readiness || {};
    const phase6 = mission.phase6_learning_loop || status.phase6_learning_loop || {};
    const phase6Certification = mission.phase6_certification || status.phase6_certification || {};
    const phase7DemoProof = mission.phase7_demo_proof || status.phase7_demo_proof || {};
    const thinking = mission.thinking || {};
    const tradeIntent = mission.trade_intent || {};
    const portfolio = mission.portfolio || {};
    const safety = mission.safety || {};
    const durable = mission.durable_spine || status.durable_ingestion || {};

    const primary = dashboardQuery("[data-mission-primary]");
    if (primary) {
        primary.innerHTML = `
            <span>Operating thesis</span>
            <h3>${htmlText(mission.headline, "Mission state unavailable")}</h3>
            <p>${htmlText(philosophy.summary, "Qadam is waiting for its trading philosophy snapshot.")}</p>
            <div class="mission-mini-grid">
                ${renderMetric("Thinking", `${thinking.hypothesis_count || 0} hyp · ${thinking.phase2_mode || "pending"}`)}
                ${renderMetric("Intent", `${tradeIntent.candidate_count || 0} candidates`)}
                ${renderMetric("Holdings", `${portfolio.open_position_count || 0} open`)}
                ${renderMetric("Replay", `${durable.replayed_source_count || 0}/${durable.expected_source_count || 0}`)}
                ${renderMetric("Safety", safety.live_capital_enabled ? "live enabled" : "live disabled")}
            </div>
            <p class="mini">${htmlText(safety.boundary, "Mission control is read-only.")}</p>
        `;
    }

    const sources = dashboardQuery("[data-mission-sources]");
    if (sources) {
        sources.innerHTML = `
            <span>Data sources</span>
            <h3>${htmlText(dataSources.logged_in_count || 0)} logged-in/configured · ${htmlText(dataSources.online_count || 0)}/${htmlText(dataSources.total_count || 0)} online</h3>
            <p>${htmlText(dataSources.degraded_count || 0)} degraded · ${htmlText(dataSources.pending_count || 0)} pending · ${htmlText(dataSources.missing_credential_count || 0)} missing credentials · replay ${htmlText(dataSources.durable_replayed_source_count || durable.replayed_source_count || 0)}/${htmlText(dataSources.durable_expected_source_count || durable.expected_source_count || 0)} ${htmlText(dataSources.durable_replay_status || durable.replay_status || "unknown")}</p>
            <p>Preference MCP ${htmlText(dataSources.preference_mcp_status, "not exported")} · identity ${htmlText(dataSources.preference_mcp_identity_status, "not verified")} · quota ${htmlText(dataSources.preference_mcp_quota_status, "unknown")} · catalog ${htmlText(dataSources.preference_mcp_catalog_status, "not run")} · ${htmlText(dataSources.preference_mcp_domain_pack_count || 0)} domain packs · provenance ${htmlText(dataSources.preference_mcp_provenance_status, "not run")} · shadow ${htmlText(dataSources.preference_mcp_shadow_context_status, "not run")}</p>
            <div class="mission-tag-row">${renderMissionTags(dataSources.logged_in_sources || dataSources.connected_sources, "No configured sources visible yet", 8)}</div>
            <small>${htmlText(dataSources.boundary, "Sources are observation only.")}</small>
        `;
    }

    const philosophyTarget = dashboardQuery("[data-mission-philosophy]");
    if (philosophyTarget) {
        philosophyTarget.innerHTML = `
            <span>Trading philosophy</span>
            <h3>${htmlText(philosophy.private_prior_count || 0)} private priors · ${htmlText(philosophy.status, "pending")}</h3>
            <p>${htmlText(asArray(philosophy.current_self_directive)[0], "Use worldview as a question generator, not proof.")}</p>
            <div class="mission-tag-row">${renderMissionTags(philosophy.decision_chain, "Decision chain not exported", 7)}</div>
            <small>${htmlText(philosophy.boundary, "Worldview is context only, not evidence.")}</small>
        `;
    }

    const stackTarget = dashboardQuery("[data-mission-stack]");
    if (stackTarget) {
        stackTarget.innerHTML = `
            <span>System stack</span>
            <h3>Orchestrator ${htmlText(stack.coo)} · Local LLM ${htmlText(stack.local_llm)}</h3>
            <p>Frontier LLM ${htmlText(stack.frontier_llm)} · quantum oracle ${htmlText(stack.quant_oracle)} via ${htmlText(stack.quant_oracle_backend, "classical_fallback")} / ${htmlText(stack.quant_oracle_mode, "not_run")} · risk ${htmlText(stack.risk_gate)}</p>
            <p>Phase 3 ${htmlText(phase3.readiness_scope, "provider/scheduler readiness")} · Q-CTRL ${phase3.qctrl_configured ? "configured" : "missing"} · Qiskit ${phase3.qiskit_available ? "yes" : "no"} / Aer ${phase3.qiskit_aer_available ? "yes" : "no"} · IBM ${htmlText(phase3.ibm_quantum_status, "unknown")} · AWS ${htmlText(phase3.aws_braket_status, "unknown")}</p>
            <p>Phase 5 ${htmlText(phase5.layer, "Layer B")} · plan ${phase5.implementation_plan_allowed ? "allowed" : "blocked"} · implementation ${phase5.implementation_allowed ? "allowed" : "blocked"} · Phase 6 plan ${phase5.phase6_learning_loop_plan_allowed ? "allowed" : "blocked"} · learning implementation ${phase5.phase6_learning_loop_implementation_allowed ? "allowed" : "blocked"} · ${htmlText(phase5.nonapproval_blocker_count || 0)} non-approval blockers</p>
            <p>Phase 6 ${htmlText(phase6.stage || "Q6-16")} · ${htmlText(phase6.learning_state || phase6.visibility_state || "not visible")} · approval ${htmlText(phase6.approval_state || "not requested")} · postmortems ${htmlText(phase6.postmortem_due_count || 0)} due / ${htmlText(phase6.postmortem_resolved_count || 0)} resolved · proposals ${(phase6.model_weight_proposal_count || 0) + (phase6.trust_score_proposal_count || 0)}</p>
            <p>Q6-17 ${htmlText(phase6Certification.status || "not_run")} · ${phase6Certification.phase6_certified ? "certified" : "not certified"} · paper growth plan ${phase6Certification.phase7_demo_proof_planning_allowed ? "allowed" : "blocked"} · blockers ${htmlText(phase6Certification.certification_blocker_count || 0)}</p>
            <p>Paper growth ${htmlText(phase7DemoProof.status || "not_run")} · day ${htmlText(phase7DemoProof.completed_calendar_day_count || 0)}/${htmlText(phase7DemoProof.phase7_harness_day_count || 30)} · week ${htmlText(phase7DemoProof.current_proof_week_number || 0)}/${htmlText(phase7DemoProof.proof_week_count || 0)} · verified paper trades ${htmlText(phase7DemoProof.closed_proof_trade_count || 0)}/${htmlText(phase7DemoProof.mature_benchmark || 100)} · weekly review ${phase7DemoProof.q7_16_weekly_review_pack_stage_allowed ? "allowed" : "blocked"}</p>
            <div class="mission-tag-row">
                ${renderInlineBadge(`data ${dashboardText(stack.data_spine)}`, stack.data_spine)}
                ${renderInlineBadge(`replay ${dashboardText(stack.durable_spine || durable.contract_status)}`, durable.status || stack.durable_spine)}
                ${renderInlineBadge(`phase2 ${dashboardText(thinking.phase2_mode || "not_run")}`, thinking.phase2_status || thinking.status)}
                ${renderInlineBadge(`Q-CTRL ${phase3.qctrl_configured ? "configured" : "missing"}`, phase3.qctrl_configured ? "configured" : "missing")}
                ${renderInlineBadge(`scheduler ${phase3.scheduler_enabled ? "enabled" : "blocked"}`, phase3.scheduler_enabled ? "blocked" : "online")}
                ${renderInlineBadge(`hardware ${phase3.hardware_submission_allowed_count ? "open" : "blocked"}`, phase3.hardware_submission_allowed_count ? "blocked" : "online")}
                ${renderInlineBadge(`oracle ${dashboardText(phase3.latest_recommendation || stack.quant_oracle_recommendation || "not_run")}`, stack.quant_oracle)}
                ${renderInlineBadge(`route ${dashboardText(phase3.latest_output_route_type || "not_run")}`, phase3.latest_output_routing_status || "pending")}
                ${renderInlineBadge(`exec ${dashboardText(phase3.execution_allowed_count || 0)}`, phase3.execution_allowed_count ? "blocked" : "online")}
                ${renderInlineBadge(`Preference ${dashboardText(stack.preference_mcp, "not_configured")}`, stack.preference_mcp)}
                ${renderInlineBadge(`Phase 5 ${dashboardText(stack.phase5_layer_b || phase5.status || "not_run")}`, phase5.implementation_allowed ? "online" : "blocked")}
                ${renderInlineBadge(`Q5-6 ${dashboardText(stack.phase5_paper_order_staging || phase5.paper_order_staging_status || "not_run")}`, phase5.paper_order_staged_count ? "online" : "blocked")}
                ${renderInlineBadge(`Q5-7 ${dashboardText(stack.phase5_alpaca_paper_dry_run || phase5.alpaca_paper_dry_run_status || "not_run")}`, phase5.alpaca_paper_dry_run_broker_post_called ? "blocked" : "pending")}
                ${renderInlineBadge(`Q5-8 ${dashboardText(stack.phase5_paper_submit_enablement || phase5.paper_submit_enablement_status || "not_run")}`, phase5.paper_submit_path_available_count ? "online" : "blocked")}
                ${renderInlineBadge(`Q5-9 ${dashboardText(stack.phase5_prediction_market_adapter || phase5.prediction_market_adapter_status || "not_run")}`, phase5.prediction_market_write_allowed_count ? "blocked" : (phase5.prediction_market_context_count ? "online" : "pending"))}
                ${renderInlineBadge(`Q5-10 ${dashboardText(stack.phase5_telegram_notifier || phase5.telegram_notifier_status || "not_run")}`, phase5.telegram_notifier_live_send_allowed_count ? "blocked" : (phase5.telegram_notifier_queued_count ? "online" : "pending"))}
                ${renderInlineBadge(`Q5-11 ${dashboardText(stack.phase5_position_monitor || phase5.position_monitor_status || "not_run")}`, phase5.position_monitor_failed_reconciliation_count ? "blocked" : "pending")}
                ${renderInlineBadge(`Q5-12 ${dashboardText(stack.phase5_signal_review || phase5.signal_review_status || "not_run")}`, phase5.signal_review_ui_inferred_readiness_count || phase5.signal_review_order_place_control_count || phase5.signal_review_broker_write_allowed_count ? "blocked" : (phase5.signal_review_record_count ? "online" : "pending"))}
                ${renderInlineBadge(`Q5-13 ${dashboardText(stack.phase5_system_map || phase5.system_map_status || "not_run")}`, phase5.system_map_backend_parity_error_count || phase5.system_map_unsafe_control_count || phase5.system_map_dashboard_claims_trading_now ? "blocked" : (phase5.system_map_node_count ? "online" : "pending"))}
                ${renderInlineBadge(`Q5-14 ${dashboardText(stack.phase5_paper_trade_drill || phase5.paper_trade_drill_status || "not_run")}`, phase5.paper_trade_drill_exit_gate_passed ? "online" : (phase5.paper_trade_drill_implementation_ready ? "blocked" : "pending"))}
                ${renderInlineBadge(`Q5-15 ${dashboardText(stack.phase5_certification || phase5.certification_status || "not_run")}`, phase5.certification_phase5_certified ? "online" : "blocked")}
                ${renderInlineBadge(`Q5E-10 ${dashboardText(stack.phase5_phase6_handoff || phase5.phase6_handoff_status || "not_run")}`, phase5.phase6_learning_loop_plan_allowed && !phase5.phase6_learning_loop_implementation_allowed ? "online" : "blocked")}
                ${renderInlineBadge(`Q6 plan ${phase5.phase6_learning_loop_plan_allowed ? "allowed" : "blocked"}`, phase5.phase6_learning_loop_plan_allowed ? "online" : "blocked")}
                ${renderInlineBadge(`Q6 writes ${phase5.phase6_learning_write_allowed || phase5.phase6_knowledge_graph_write_allowed ? "open" : "blocked"}`, phase5.phase6_learning_write_allowed || phase5.phase6_knowledge_graph_write_allowed ? "blocked" : "online")}
                ${renderInlineBadge(`Q6-16 ${dashboardText(stack.phase6_learning_loop || phase6.status || "not_run")}`, phase6.backend_derived && !phase6.ui_inferred_readiness_count ? "online" : "blocked")}
                ${renderInlineBadge(`Q6-17 ${dashboardText(phase6Certification.status || "not_run")}`, phase6Certification.phase6_certified ? "online" : "blocked")}
                ${renderInlineBadge(`paper growth ${phase6Certification.phase7_demo_proof_planning_allowed ? "allowed" : "blocked"}`, phase6Certification.phase7_demo_proof_planning_allowed ? "online" : "blocked")}
                ${renderInlineBadge(`growth status ${dashboardText(stack.phase7_demo_proof || phase7DemoProof.status || "not_run")}`, phase7DemoProof.backend_derived && !phase7DemoProof.ui_inferred_readiness_count ? "online" : "blocked")}
                ${renderInlineBadge(`growth maturity ${htmlText(phase7DemoProof.closed_proof_trade_count || 0)}/${htmlText(phase7DemoProof.mature_benchmark || 100)}`, phase7DemoProof.phase7_mature_benchmark_met ? "online" : "pending")}
                ${renderInlineBadge(phase7DemoProof.phase7_proof_credit_allowed ? "paper growth maturity open" : "no false growth maturity", phase7DemoProof.phase7_proof_credit_allowed ? "blocked" : "online")}
                ${renderInlineBadge(`learning ${dashboardText(phase6.learning_state || "not_run")}`, phase6.learning_state === "blocked_pending_learning_approval" ? "blocked" : "online")}
                ${renderInlineBadge(`UI inferred ${phase6.ui_inferred_readiness_count || 0}`, phase6.ui_inferred_readiness_count ? "blocked" : "online")}
                ${renderInlineBadge(`blocked authorities ${phase6.blocked_authority_count || 0}`, phase6.blocked_authority_count ? "online" : "blocked")}
                ${renderInlineBadge(`Layer B plan ${phase5.implementation_plan_allowed ? "allowed" : "blocked"}`, phase5.implementation_plan_allowed ? "pending" : "blocked")}
                ${renderInlineBadge(`paper ${dashboardText(stack.paper_account)}`, stack.paper_account)}
                ${renderInlineBadge(`telegram ${dashboardText(stack.telegram)}`, stack.telegram)}
            </div>
            <small>${htmlText(phase3.boundary || stack.boundary, "Phase 3 is provider/scheduler readiness only, not execution readiness.")}</small>
        `;
    }

    const strategyTarget = dashboardQuery("[data-mission-strategy]");
    if (strategyTarget) {
        const approvalState = phase4.approval_event_status || phase4.approval_event?.approval_state || "missing";
        const toggleCount = phase4.toggle_count || phase4.strategy_toggles?.toggle_count || 0;
        const approvedShadowCount = phase4ApprovedShadowCount(phase4);
        strategyTarget.innerHTML = `
            <span>Phase 4 strategy</span>
            <h3>${htmlText(phase4.stage || "Q4-11")} · ${htmlText(approvalState)}</h3>
            <p>Document ${htmlText(phase4.strategy_document_status, "missing")} · ${htmlText(toggleCount)} visible toggles · ${htmlText(approvedShadowCount)} approved-shadow · certification ${htmlText(phase4.certification_status || (phase4.phase4_certification_allowed ? "allowed" : "blocked"))}</p>
            <div class="mission-tag-row">
                ${renderInlineBadge(`stage ${dashboardText(phase4.stage_status, "pending")}`, phase4.stage_status || "pending")}
                ${renderInlineBadge(`approval ${dashboardText(approvalState)}`, phase4ApprovalTone(phase4))}
                ${renderInlineBadge(`toggles ${toggleCount}`, toggleCount ? "pending" : "blocked")}
                ${renderInlineBadge(`approved-shadow ${approvedShadowCount}`, approvedShadowCount ? "online" : "blocked")}
            </div>
            <small>${htmlText(phase4.boundary || phase4.no_execution_boundary, "Phase 4 strategy visibility is governance-only and non-executable.")}</small>
        `;
    }

    const trades = dashboardQuery("[data-mission-trades]");
    if (trades) {
        const candidateNames = asArray(tradeIntent.top_candidates).map((item) => {
            const direction = item.direction ? ` ${item.direction}` : "";
            return `${item.instrument || "candidate"}${direction}`;
        });
        const blockedNames = asArray(tradeIntent.blocked_trades).map((item) => `${item.instrument || "blocked idea"}: ${item.blocked_reason || item.status || "blocked"}`);
        trades.innerHTML = `
            <span>Trade intent</span>
            <h3>${htmlText(tradeIntent.state, "no trade candidate")}</h3>
            <p>${htmlText(tradeIntent.summary, "No executable trade candidate exists.")}</p>
            <div class="mission-mini-grid compact">
                ${renderMetric("Observed", tradeIntent.observed_signal_count || 0)}
                ${renderMetric("Candidates", tradeIntent.candidate_count || 0)}
                ${renderMetric("Blocked", tradeIntent.blocked_count || 0)}
                ${renderMetric("Submitted", tradeIntent.paper_order_submitted_count || 0)}
            </div>
            <div class="mission-tag-row">${renderMissionTags(candidateNames.length ? candidateNames : blockedNames, "No candidate or blocked trade visible yet", 4)}</div>
            <small>${htmlText(tradeIntent.boundary, "Candidate is not order.")}</small>
        `;
    }

    const portfolioTarget = dashboardQuery("[data-mission-portfolio]");
    if (portfolioTarget) {
        const portfolioMoney = (value) => formatMoney(value, capitalCurrency(portfolio));
        const openPositionNames = asArray(portfolio.open_positions).map((position) => {
            const pnl = position.unrealized_pnl_gbp === undefined ? "" : ` ${portfolioMoney(position.unrealized_pnl_gbp)}`;
            return `${position.instrument || "position"}${pnl}`;
        });
        const orderNames = asArray(portfolio.orders).map((order) => `${order.instrument || "order"} ${order.status || "mirrored"}`);
        const reconciliationStatus = dashboardText(portfolio.portfolio_reconciliation?.status, "not available");
        portfolioTarget.innerHTML = `
            <span>Paper account</span>
            <h3>${portfolioMoney(portfolio.current_balance_gbp)} · ${portfolioMoney(portfolio.total_pnl_gbp)} P&L</h3>
            <p>${htmlText(portfolio.connection_status, "pending")} · ${htmlText(portfolio.mirror_freshness_label, "freshness unknown")} · ${htmlText(portfolio.portfolio_value_source, "paper mirror")} · history ${htmlText(reconciliationStatus)}</p>
            <div class="mission-mini-grid compact">
                ${renderMetric("Open", portfolio.open_position_count || 0)}
                ${renderMetric("Orders", portfolio.order_count || 0)}
                ${renderMetric("Closed", portfolio.closed_trade_count || 0)}
                ${renderMetric("Write", portfolio.write_authority ? "enabled" : "blocked")}
            </div>
            <div class="mission-tag-row">${renderMissionTags(openPositionNames.length ? openPositionNames : orderNames, "No open positions or mirrored orders", 4)}</div>
            <small>${htmlText(portfolio.boundary, "Read-only paper account mirror.")}</small>
        `;
    }
}

function renderOperatingSummary(status, source) {
    const target = dashboardQuery("[data-operating-summary]");
    if (!target) return;

    const watching = asArray(status.watching);
    const sourceCounts = countBy(watching, "status");
    const pipelineSummary = asArray(status.source_pipeline_summary);
    const missingCredentialCount = pipelineSummary.reduce(
        (total, pipeline) => total + Number(pipeline.missing_credential_count || 0),
        0
    );
    const degradedSources = Number(sourceCounts.degraded || 0);
    const pendingSources = Number(sourceCounts.pending || 0);
    const localOnlySources = Number(sourceCounts.local_only || sourceCounts["local-only"] || 0);

    const cognition = status.cognition || {};
    const hypotheses = asArray(cognition.hypotheses);
    const shadowPackets = asArray(cognition.shadow_packets);
    const localResearch = asArray(cognition.local_research_assessments);
    const executableHypotheses = hypotheses.filter((hypothesis) => hypothesis.execution_allowed).length;

    const tradeLayer = status.trade_layer || {};
    const observedSignals = asArray(tradeLayer.watching);
    const candidates = asArray(tradeLayer.candidates);
    const blockedTrades = asArray(tradeLayer.blocked);
    const stagedOrders = asArray(tradeLayer.staged_orders);
    const submittedOrders = asArray(tradeLayer.submitted_orders);
    const paperOrders = stagedOrders.length + submittedOrders.length;

    const capital = status.capital || {};
    const maturityCount = Number(capital.maturity_closed_trade_count || 0);
    const maturityTarget = Number(capital.maturity_closed_trade_target || 100);
    const realized = Number(capital.realized_pnl_gbp || 0);
    const unrealized = Number(capital.unrealized_pnl_gbp || 0);
    const pnlTotal = realized + unrealized;
    const money = (value) => formatCapitalMoney(value, capital);

    const forbiddenActions = asArray(status.forbidden_actions);
    const liveCapital = Boolean(capital.live_capital_enabled);
    const brokerWriteBlocked = forbiddenActions.some((action) => /broker|write/i.test(`${action.action || ""} ${action.reason || ""}`));
    const liveBridge = status.live_bridge || {};
    const bridgeLabel = source?.key === "live_bridge" ? "Live status" : "Sanitized status";
    const bridgeMeta = liveBridge.status === "read_only_ready" ? "read-only ready" : dashboardText(liveBridge.status, "bridge pending");
    const phase4 = phase4StrategyStatus(status);
    const phase4ApprovalState = phase4.approval_event_status || phase4.approval_event?.approval_state || "missing";
    const phase4ToggleCount = phase4.toggle_count || phase4.strategy_toggles?.toggle_count || 0;
    const phase4ApprovedShadowTotal = phase4ApprovedShadowCount(phase4);

    target.innerHTML = [
        renderPriorityCard(
            "Paper account",
            money(capital.current_balance_gbp),
            `${money(pnlTotal)} total P&L · ${formatPercent(capital.drawdown_pct)} drawdown · ${maturityCount}/${maturityTarget} closed paper trades`,
            "Authority shown in Safety Status",
            capital.live_capital_enabled ? "blocked" : "online"
        ),
        renderPriorityCard(
            "Source quality",
            `${sourceCounts.online || 0}/${watching.length} online`,
            `${degradedSources} degraded · ${pendingSources} pending · ${localOnlySources} local-only · ${missingCredentialCount} missing credentials`,
            "Evidence strength depends on source health",
            degradedSources || missingCredentialCount ? "degraded" : "online"
        ),
        renderPriorityCard(
            "Cognition",
            `${hypotheses.length} hypotheses`,
            `${shadowPackets.length} shadow packets · ${localResearch.length} local assessments · ${executableHypotheses} executable`,
            executableHypotheses ? "Unexpected execution permission" : "Research only",
            executableHypotheses ? "blocked" : "pending"
        ),
        renderPriorityCard(
            "Strategy",
            `${phase4.stage || "Q4"} ${dashboardText(phase4ApprovalState)}`,
            `Document ${dashboardText(phase4.strategy_document_status, "missing")} · ${phase4ToggleCount} toggles · ${phase4ApprovedShadowTotal} approved-shadow`,
            phase4.phase4_certification_allowed
                ? "Phase 4 certification allowed"
                : "Missing approval blocks Phase 4 certification",
            phase4ApprovalTone(phase4)
        ),
        renderPriorityCard(
            "Trade layer",
            `${candidates.length} candidates`,
            `${observedSignals.length} observed · ${blockedTrades.length} blocked · ${paperOrders} staged/submitted paper orders`,
            "Candidate is not order",
            paperOrders ? "pending" : "online"
        ),
        renderPriorityCard(
            "Safety strip",
            liveCapital ? "Authority review" : "Single strip clear",
            `${forbiddenActions.length} safety stops · broker writes ${brokerWriteBlocked ? "stopped" : "not recorded"} · use the single strip for dashboard authority`,
            "One authority readout for every view",
            liveCapital ? "blocked" : "online"
        ),
        renderPriorityCard(
            "Bridge",
            bridgeLabel,
            `${bridgeMeta} · snapshot ${formatTime(status.generated_at)} · schema ${dashboardText(status.schema_version, "unknown")}`,
            source?.key === "live_bridge" ? "Serving protected status endpoint" : "Serving static safe snapshot",
            source?.key === "live_bridge" ? "online" : "pending"
        )
    ].join("");
}

const OVERVIEW_NODE_LABELS = {
    watching: "Live data feeds",
    event_log: "Python script",
    research_analyst: "Local LLM",
    strategy_lead: "Frontier LLM",
    head_of_quant: "Quantum computer",
    risk_agent: "Risk gate",
    trade_layer: "Trade lifecycle",
    postmortem_loop: "Learning loop"
};

const OVERVIEW_NODE_ROLES = {
    watching: "Intelligence pipelines",
    event_log: "Orchestrator",
    research_analyst: "Research Analyst",
    strategy_lead: "Strategy Lead",
    head_of_quant: "Head of Quant",
    risk_agent: "Safety policy",
    trade_layer: "Paper/demo state",
    postmortem_loop: "Learning review"
};

const OVERVIEW_NODE_GUIDES = {
    watching: {
        does: "This is where Qadam sees the world: macro, conflict, logistics, broker, market, social, and supplemental data.",
        watch: "Healthy means the feeds are fresh enough to support evidence review; it does not mean a trade is approved.",
        handoff: "Observed facts move to the Python orchestrator and evidence ledger."
    },
    event_log: {
        does: "The Python COO writes the audit trail, exports the sanitized dashboard snapshot, and keeps local runtime state replayable.",
        watch: "Look for stale exports, failed checks, or any authority flag that would make the cockpit unsafe.",
        handoff: "Clean status becomes the public read-only dashboard."
    },
    research_analyst: {
        does: "The local LLM compresses noisy observations into shadow research so raw feed noise does not become a trade idea too quickly.",
        watch: "Its output is useful when it has processed evidence packets, but it remains compression-only and cannot approve risk or orders.",
        handoff: "Research packets move to Strategy Lead challenge review."
    },
    strategy_lead: {
        does: "The frontier LLM challenges the current thesis, checks the strategy family, and asks what would invalidate the idea.",
        watch: "A healthy Strategy Lead means the idea has been challenged, not approved. Missing challenge notes keep the idea in review.",
        handoff: "Challenged ideas move to signal integrity, risk, and paper-only lifecycle gates."
    },
    head_of_quant: {
        does: "The quantum/classical quant desk runs bounded scenario checks and reports whether hardware or classical fallback is being used.",
        watch: "It can annotate uncertainty and comparison value, but it is not allowed to originate, approve, or place trades.",
        handoff: "Quant annotations become one input to the risk and signal gates."
    },
    risk_agent: {
        does: "This gate checks whether evidence, policy, sizing, kill switches, and execution boundaries allow the idea to continue.",
        watch: "Any blocked status here is intentional until the relevant proof or approval exists.",
        handoff: "Only guarded paper-eligible records can move onward."
    },
    trade_layer: {
        does: "This is the paper/demo lifecycle: candidates, staged paper orders, submitted paper orders, positions, exits, and postmortems.",
        watch: "Read the stage carefully. A candidate is not an order; a paper order is not live capital.",
        handoff: "Closed paper outcomes move to postmortem and learning review."
    },
    postmortem_loop: {
        does: "The learning loop compares closed paper outcomes against the original thesis and records what Qadam should learn.",
        watch: "Learning proposals stay deferred until governance explicitly approves changes.",
        handoff: "Approved lessons can later update trusted memory, strategy, or source weighting."
    }
};

function overviewNodeGuide(node = {}, role = "", label = "") {
    const guide = OVERVIEW_NODE_GUIDES[node.key] || {};
    const expanded = node.expanded || {};
    const current = dashboardText(expanded.current_process || node.purpose || node.status, "No current process exported.");
    const boundary = dashboardText(node.authority || expanded.current_status, "Read-only dashboard status.");
    return {
        label: label || node.label || "System node",
        role: role || node.role || "Qadam node",
        does: guide.does || dashboardText(node.purpose, "This node contributes to Qadam's operating flow."),
        current,
        watch: guide.watch || "Use this status to decide whether the next node can trust the handoff.",
        boundary,
        handoff: guide.handoff || dashboardText(expanded.handoff || node.output, "It passes sanitized state to the next review point.")
    };
}

function renderOverviewChip(chip) {
    return `
        <span class="overview-status-chip ${statusClass(chip.tone)}">
            <strong>${htmlText(chip.value)}</strong>
            <em>${htmlText(chip.label)}</em>
        </span>
    `;
}

function renderOverviewReadout(item) {
    return `
        <div class="overview-readout ${statusClass(item.tone)}">
            <span>${htmlText(item.label)}</span>
            <strong>${htmlText(item.state)}</strong>
            <p>${htmlText(item.summary)}</p>
        </div>
    `;
}

function renderOverviewLifecycleItem(item, index) {
    return `
        <li class="${statusClass(item.tone)}">
            <span>${String(index + 1).padStart(2, "0")}</span>
            <strong>${htmlText(item.label)}</strong>
            <em>${htmlText(item.count)}</em>
        </li>
    `;
}

function renderOverviewMiniNode(node, index, total) {
    const label = OVERVIEW_NODE_LABELS[node.key] || node.label;
    const role = OVERVIEW_NODE_ROLES[node.key] || node.role;
    const guide = overviewNodeGuide(node, role, label);
    const guideId = `overview-node-guide-${String(node.key || index).replace(/[^a-z0-9_-]/gi, "-")}`;
    const connector = index < total - 1 ? `<span class="overview-mini-connector" aria-hidden="true">&rarr;</span>` : "";
    return `
        <details class="overview-mini-node ${statusClass(node.health || node.status)}">
            <summary aria-controls="${guideId}">
                <div class="overview-mini-top">
                    <span class="overview-mini-step">${index + 1}</span>
                    <span class="overview-mini-role">${htmlText(role)}</span>
                </div>
                <strong>${htmlText(label)}</strong>
                <p>${htmlText(node.status)}</p>
            </summary>
            <div class="overview-mini-guide" id="${guideId}" aria-label="${htmlText(label)} guide">
                <span>How to read this node</span>
                <strong>${htmlText(guide.role)}: ${htmlText(guide.label)}</strong>
                <dl>
                    <div><dt>What it does</dt><dd>${htmlText(guide.does)}</dd></div>
                    <div><dt>Currently</dt><dd>${htmlText(guide.current)}</dd></div>
                    <div><dt>Watch for</dt><dd>${htmlText(guide.watch)}</dd></div>
                    <div><dt>Boundary</dt><dd>${htmlText(guide.boundary)}</dd></div>
                    <div><dt>Next handoff</dt><dd>${htmlText(guide.handoff)}</dd></div>
                </dl>
            </div>
        </details>
        ${connector}
    `;
}

function renderOverviewPlainCard(item) {
    return `
        <article class="overview-plain-card ${statusClass(item.tone || item.status)}">
            <span>${htmlText(item.label)}</span>
            <strong>${htmlText(item.value || item.state || item.status)}</strong>
            <p>${htmlText(item.summary)}</p>
        </article>
    `;
}

function renderOverviewSourceRow(source = {}) {
    const status = source.status || source.raw_status || "pending";
    return `
        <li class="source-row overview-source-row">
            <div class="source-main">
                ${renderStatusPill(status)}
                <div>
                    <strong>${htmlText(source.label, source.key || "Source")}</strong>
                    <span>${htmlText(source.pipeline)} · ${htmlText(source.readiness)} · ${htmlText(source.cadence)}</span>
                </div>
            </div>
            <div class="source-meta">
                ${renderInlineBadge(source.credential_status, source.credential_status === "missing" ? "degraded" : "online")}
                ${renderInlineBadge(source.promoted_adapter ? "adapter live" : "registry/pending", source.promoted_adapter ? "online" : "pending")}
                ${renderInlineBadge(source.can_influence_signals ? "signal input" : "evidence only", source.can_influence_signals ? "online" : "optional")}
                ${renderInlineBadge(`tier ${dashboardText(source.tier, "n/a")}`, source.tier ? "online" : "pending")}
                ${renderInlineBadge(`trust ${dashboardText(source.trust_score, "n/a")}`, source.trust_score ? "online" : "pending")}
                ${renderInlineBadge(formatTime(source.heartbeat), status)}
            </div>
            <p>${htmlText(source.degraded_reason || source.raw_status || status)} · ${htmlText(source.influence_boundary)}</p>
        </li>
    `;
}

function renderOverviewSourcePipeline(pipeline = {}) {
    const sources = asArray(pipeline.sources);
    return `
        <details class="overview-ledger-group">
            <summary>
                <strong>${htmlText(OPERATIONS_PIPELINE_LABELS[pipeline.pipeline] || pipeline.label || pipeline.pipeline, "Source pipeline")}</strong>
                <span>${htmlText(pipeline.online_count, "0")}/${htmlText(pipeline.source_count, sources.length)} connected · ${htmlText(pipeline.degraded_count, "0")} degraded · ${htmlText(pipeline.pending_count, "0")} pending</span>
            </summary>
            <ul class="source-table">
                ${sources.map(renderOverviewSourceRow).join("")}
            </ul>
        </details>
    `;
}

function renderOverviewStrategyRow(strategy = {}) {
    const blockedAuthority = [
        strategy.execution_allowed ? "execution allowed" : "no execution",
        strategy.paper_order_allowed ? "paper order allowed" : "no paper order",
        strategy.broker_write_allowed ? "broker write allowed" : "no broker write",
        strategy.live_capital_enabled ? "live capital enabled" : "live capital off"
    ];
    const unsafeTone = strategy.execution_allowed || strategy.paper_order_allowed || strategy.broker_write_allowed || strategy.live_capital_enabled ? "blocked" : "online";
    return `
        <li class="source-row overview-strategy-row">
            <div class="source-main">
                ${renderStatusPill(strategy.tone || strategy.approval_state)}
                <div>
                    <strong>${htmlText(strategy.label, strategy.key || "Strategy family")}</strong>
                    <span>${htmlText(strategy.approval_state)} · ${htmlText(strategy.toggle_state)} · ${strategy.visible_in_cockpit ? "visible in cockpit" : "not cockpit-visible"}</span>
                </div>
            </div>
            <div class="source-meta">
                ${renderInlineBadge(strategy.value || strategy.status || "review state", strategy.tone)}
                ${blockedAuthority.map((label) => renderInlineBadge(label, label.startsWith("no ") || label.includes("off") ? "online" : unsafeTone)).join("")}
                ${renderInlineBadge(strategy.event_log_required ? "event log required" : "event log not required", strategy.event_log_required ? "online" : "pending")}
            </div>
            <p>${htmlText(strategy.summary)} ${htmlText(strategy.boundary)}</p>
        </li>
    `;
}

function renderOverviewThoughtItem(item) {
    return `
        <li class="${statusClass(item.tone || item.status)}">
            <span>${htmlText(item.label)}</span>
            <strong>${htmlText(item.value || item.status)}</strong>
            <p>${htmlText(item.summary)}</p>
        </li>
    `;
}

function renderOverviewCapacityChart(capacity = {}) {
    const chartPoints = asArray(capacity.equity_curve).length
        ? asArray(capacity.equity_curve)
        : paperAccountEquityPoints({
            current_balance_gbp: capacity.equity_gbp,
            equity_gbp: capacity.equity_gbp,
            observed_at: capacity.observed_at,
            drawdown_pct: capacity.drawdown_pct
        });
    const stats = paperAccountEquityStats(chartPoints);
    const width = 520;
    const height = 150;
    const left = 66;
    const right = 16;
    const top = 18;
    const bottom = 28;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const rawMin = stats.min;
    const rawMax = stats.max;
    const range = rawMax - rawMin;
    const padding = range > 0 ? range * 0.18 : Math.max(10, Math.abs(rawMax || 1000) * 0.01);
    const min = rawMin - padding;
    const max = rawMax + padding;
    const yFor = (value) => top + ((max - value) / (max - min || 1)) * plotHeight;
    const xFor = (index) => left + (chartPoints.length <= 1 ? plotWidth / 2 : (index / (chartPoints.length - 1)) * plotWidth);
    const path = chartPoints
        .map((point, index) => `${index ? "L" : "M"} ${xFor(index).toFixed(2)} ${yFor(point.equity_gbp).toFixed(2)}`)
        .join(" ");
    const usedWidth = Math.round(Math.min(1, Math.max(0, Number(capacity.used_fraction || 0))) * 100);
    const targetWidth = Math.round(Math.min(1, Math.max(0, Number(capacity.target_progress_fraction || 0))) * 100);

    return `
        <div class="overview-capacity-chart-card ${statusClass(capacity.tone || "online")}">
            <svg class="overview-capacity-line" viewBox="0 0 ${width} ${height}" role="img" aria-label="Paper account capacity line" preserveAspectRatio="none" data-paper-capacity-line>
                <line class="chart-grid-line" x1="${left}" y1="${height - bottom}" x2="${width - right}" y2="${height - bottom}"></line>
                <line class="chart-grid-line muted" x1="${left}" y1="${yFor(stats.max).toFixed(2)}" x2="${width - right}" y2="${yFor(stats.max).toFixed(2)}"></line>
                <line class="chart-grid-line muted" x1="${left}" y1="${yFor(stats.min).toFixed(2)}" x2="${width - right}" y2="${yFor(stats.min).toFixed(2)}"></line>
                <path class="paper-equity-line" d="${path}"></path>
                <text class="chart-axis-label" x="4" y="${yFor(stats.max).toFixed(2)}">${literalHtmlText(formatMoney(stats.max))}</text>
                <text class="chart-axis-label" x="4" y="${yFor(stats.min).toFixed(2)}">${literalHtmlText(formatMoney(stats.min))}</text>
                <text class="chart-axis-label chart-axis-last" x="${width - right}" y="${height - 8}">${literalHtmlText(formatTime(capacity.observed_at))}</text>
            </svg>
            <div class="overview-capacity-bar" aria-label="Paper capacity deployed">
                <span style="width: ${usedWidth}%"></span>
            </div>
            <div class="overview-capacity-bar target" aria-label="Paper growth target progress">
                <span style="width: ${targetWidth}%"></span>
            </div>
            <div class="overview-capacity-summary">
                ${renderMetric("Deployed", formatMoney(capacity.deployed_gbp))}
                ${renderMetric("Start", formatMoney(capacity.total_gbp))}
                ${renderMetric("Equity", formatMoney(capacity.equity_gbp))}
                ${renderMetric("Target", formatMoney(capacity.target_gbp))}
                ${renderMetric("P&L", formatMoney(capacity.total_pnl_gbp))}
            </div>
        </div>
    `;
}

function renderOverviewFirstScreen(viewModels) {
    const overview = viewModels?.overview_model;
    const connectivity = viewModels?.system_connectivity_model;
    if (!overview || !connectivity) return;

    const proof = overview.demo_proof || {};
    const readouts = asArray(overview.readouts || overview.cards);
    const review = overview.review_focus || {};
    const setupText = `${proof.eligible_setup_count || 0} potential setups`;
    const proofText = `${proof.closed_proof_trade_count || 0}/${proof.mature_benchmark || 100} verified paper trades`;

    const statusRail = dashboardQuery("[data-overview-status-rail]");
    if (statusRail) {
        statusRail.innerHTML = asArray(overview.status_chips)
            .map(renderOverviewChip)
            .join("");
    }

    const hero = dashboardQuery("[data-overview-hero]");
    if (hero) {
        hero.innerHTML = `
            <span>Current summary</span>
            <h3>${htmlText(overview.summary)}</h3>
            <p>${htmlText(overview.scope_note || overview.boundary)}</p>
            <div class="overview-hero-metrics" data-overview-hero-metrics>
                ${renderMetric("Paper growth", `${formatMoney(overview.paper_capacity?.equity_gbp || 0)} / ${formatMoney(overview.paper_capacity?.target_gbp || 0)}`)}
                ${renderMetric("Setups", setupText)}
                ${renderMetric("Next review", review.state || "Continue monitoring")}
            </div>
            <div class="overview-readout-list" data-overview-metrics>
                ${readouts.slice(0, 4).map(renderOverviewReadout).join("")}
            </div>
        `;
    }

    const reviewCard = dashboardQuery("[data-overview-review-card]");
    if (reviewCard) {
        reviewCard.classList.remove("online", "pending", "degraded", "blocked");
        reviewCard.classList.add(statusClass(review.tone || "online"));
        reviewCard.innerHTML = `
            <span>Needs review</span>
            <strong data-overview-action-label>${htmlText(review.state || "Continue monitoring")}</strong>
            <p data-overview-action-summary>${htmlText(review.summary || "No immediate action visible.")}</p>
            <nav class="overview-next-links" aria-label="Next review links" data-overview-next-links>
                ${asArray(overview.next_review_links).map((link) => `
                    <a href="${htmlText(link.href)}">
                        <strong>${htmlText(link.label)}</strong>
                        <span>${htmlText(link.reason)}</span>
                    </a>
                `).join("")}
            </nav>
        `;
    }

    const systemStatus = dashboardQuery("[data-overview-system-status]");
    if (systemStatus) {
        systemStatus.innerHTML = `
            <div class="overview-section-head">
                <span>System status</span>
                <strong>Plain-language runtime state</strong>
            </div>
            <div class="overview-plain-card-grid">
                ${asArray(overview.system_status).map(renderOverviewPlainCard).join("")}
            </div>
        `;
    }

    const paperCapacity = dashboardQuery("[data-overview-paper-capacity]");
    if (paperCapacity) {
        const capacity = overview.paper_capacity || {};
        paperCapacity.innerHTML = `
            <div class="overview-section-head">
                <span>Paper capacity</span>
                <strong>${formatMoney(capacity.equity_gbp)} toward ${formatMoney(capacity.target_gbp)} in ${htmlText(capacity.target_horizon_days)} days</strong>
            </div>
            <p>${htmlText(capacity.summary, "Paper capacity has not loaded.")}</p>
            ${renderOverviewCapacityChart(capacity)}
        `;
    }

    const metrics = dashboardQuery("[data-overview-metrics]");
    if (metrics) {
        metrics.innerHTML = readouts.slice(0, 4)
            .map(renderOverviewReadout)
            .join("");
    }

    setText("[data-overview-lifecycle-summary]", overview.lifecycle_summary || `${setupText}; ${proofText}.`);
    const lifecycle = dashboardQuery("[data-overview-lifecycle]");
    if (lifecycle) {
        lifecycle.innerHTML = asArray(overview.lifecycle)
            .map(renderOverviewLifecycleItem)
            .join("");
    }

    const oversight = dashboardQuery("[data-overview-oversight]");
    if (oversight) {
        oversight.innerHTML = `
            <span>Fund Manager oversight</span>
            <strong>You supervise Qadam</strong>
            <p>${htmlText(overview.system_summary || "Live feeds, Python, models, gates, paper lifecycle, and learning loop stay visible from one map.")}</p>
        `;
    }

    const miniMap = dashboardQuery("[data-overview-mini-map]");
    if (miniMap) {
        const nodeByKey = new Map(asArray(connectivity.nodes).map((node) => [node.key, node]));
        const miniNodes = asArray(overview.mini_map?.node_keys)
            .map((key) => nodeByKey.get(key))
            .filter(Boolean);
        miniMap.innerHTML = miniNodes.length
            ? miniNodes.map((node, index) => renderOverviewMiniNode(node, index, miniNodes.length)).join("")
            : `<span>No system connectivity nodes are visible yet.</span>`;
    }

    const feeds = dashboardQuery("[data-overview-feed-strip]");
    if (feeds) {
        feeds.innerHTML = asArray(connectivity.feed_clusters).slice(0, 3).map((feed) => `
            <span class="${statusClass(feed.status)}">
                <strong>${htmlText(feed.label)}</strong>
                ${htmlText(feed.status)} · ${htmlText(feed.count)} records
            </span>
        `).join("");
    }

    const boundary = dashboardQuery("[data-overview-boundary-rail]");
    if (boundary) {
        boundary.innerHTML = `
            <span>How to read this</span>
            <p>${htmlText(overview.scope_note || "Use Safety Status for order authority.")} A trade idea is not an order.</p>
        `;
    }

    const dataSources = dashboardQuery("[data-overview-data-sources]");
    if (dataSources) {
        const visibleSources = asArray(overview.data_sources_connected).slice(0, 4);
        const sourceModel = viewModels?.sources_model || {};
        const allSources = asArray(sourceModel.all_sources);
        const pipelines = asArray(sourceModel.pipelines);
        const connectedCount = modelNumber(sourceModel.counts?.online, visibleSources.length);
        const totalCount = modelNumber(sourceModel.counts?.total, allSources.length || visibleSources.length);
        dataSources.innerHTML = `
            <details class="overview-expandable-ledger" data-overview-source-ledger>
                <summary>
                    <span>Data sources connected</span>
                    <strong>${connectedCount}/${totalCount} connected</strong>
                    <em>Click to expand the full source list and connection state.</em>
                </summary>
                <div class="overview-ledger-body">
                    <p>${htmlText(sourceModel.summary, "Source health has not loaded.")}</p>
                    <div class="overview-plain-card-grid">
                        ${visibleSources.map(renderOverviewPlainCard).join("")}
                    </div>
                    <div class="overview-ledger-list">
                        ${pipelines.length
            ? pipelines.map(renderOverviewSourcePipeline).join("")
            : `<ul class="source-table">${allSources.map(renderOverviewSourceRow).join("")}</ul>`}
                    </div>
                </div>
            </details>
        `;
    }

    const strategies = dashboardQuery("[data-overview-trading-strategies]");
    if (strategies) {
        const visibleStrategies = asArray(overview.trading_strategies).slice(0, 5);
        const allStrategies = asArray(overview.trading_strategies);
        const approvedCount = allStrategies.filter((strategy) => strategy.approval_state === "approved").length;
        strategies.innerHTML = `
            <details class="overview-expandable-ledger" data-overview-strategy-ledger>
                <summary>
                    <span>Trading strategies</span>
                    <strong>${approvedCount}/${allStrategies.length || visibleStrategies.length} approved-shadow</strong>
                    <em>Click to expand every strategy family Qadam is allowed to consider.</em>
                </summary>
                <div class="overview-ledger-body">
                    <p>These are research and governance toggles. They tell Qadam what style of thesis it may consider; they do not approve orders.</p>
                    <div class="overview-plain-card-grid strategy-grid">
                        ${visibleStrategies.map(renderOverviewPlainCard).join("")}
                    </div>
                    <ul class="source-table">
                        ${allStrategies.map(renderOverviewStrategyRow).join("")}
                    </ul>
                </div>
            </details>
        `;
    }

    const thoughtFeed = dashboardQuery("[data-overview-thought-feed]");
    if (thoughtFeed) {
        const visibleThoughts = asArray(overview.thought_feed)
            .filter((item) => item.label !== "Current focus")
            .slice(0, 4);
        thoughtFeed.innerHTML = `
            <div class="overview-section-head">
                <span>Qadam's thoughts</span>
                <strong>Current reasoning feed</strong>
            </div>
            <ol class="overview-thought-list">
                ${visibleThoughts.map(renderOverviewThoughtItem).join("")}
            </ol>
        `;
    }

    const tradeConsiderations = dashboardQuery("[data-overview-trade-considerations]");
    if (tradeConsiderations) {
        const visibleTradeIdeas = asArray(overview.trade_considerations).slice(0, 5);
        tradeConsiderations.innerHTML = `
            <div class="overview-section-head">
                <span>Trades being considered</span>
                <strong>${htmlText(visibleTradeIdeas.length)} live ideas</strong>
            </div>
            <div class="overview-plain-card-grid">
                ${visibleTradeIdeas.length
        ? visibleTradeIdeas.map(renderOverviewPlainCard).join("")
        : `<article class="overview-plain-card online"><span>No active trade idea</span><strong>Monitoring only</strong><p>Qadam has not exported an observed signal or candidate in this snapshot.</p></article>`}
            </div>
            <p class="mini">Candidate, not order. A candidate is still only something Qadam is thinking about.</p>
        `;
    }

    const nextLinks = dashboardQuery("[data-overview-next-links]");
    if (nextLinks) {
        nextLinks.innerHTML = asArray(overview.next_review_links).map((link) => `
            <a href="${htmlText(link.href)}">
                <strong>${htmlText(link.label)}</strong>
                <span>${htmlText(link.reason)}</span>
            </a>
        `).join("");
    }
}

function renderTradesWorkspaceFilter(filter, active = false) {
    return `
        <button type="button" data-trade-lifecycle-filter="${literalHtmlText(filter.id)}" aria-pressed="${active ? "true" : "false"}">
            <span>${htmlText(filter.label)}</span>
            <strong>${htmlText(filter.count)}</strong>
        </button>
    `;
}

function renderTradeLifecycleCard(record) {
    const references = asArray(record.references).map((reference) => `
        <a href="${htmlText(reference.href)}">
            <strong>${htmlText(reference.label)}</strong>
            <span>${htmlText(reference.status)}</span>
        </a>
    `).join("");
    return `
        <article class="trade-lifecycle-card ${statusClass(record.tone)}"
            data-trade-lifecycle-card
            data-filter-states="${literalHtmlText(asArray(record.filters).join(" "))}"
            data-proof-scope="${literalHtmlText(record.proof_scope)}">
            <div class="trade-lifecycle-topline">
                ${renderStatusPill(record.status)}
                <span>${htmlText(record.stage_label)}</span>
                <span>${htmlText(record.proof_scope_label)}</span>
            </div>
            <h3>${htmlText(record.title)}</h3>
            <p>${htmlText(record.summary)}</p>
            <div class="summary-strip compact">
                ${renderMetric("Instrument", record.instrument)}
                ${renderMetric("Direction", record.direction)}
                ${renderMetric("Observed", formatTime(record.observed_at))}
                ${renderMetric("Risk", record.risk_decision)}
                ${renderMetric("Source quorum", record.source_quorum_status)}
                ${renderMetric("Broker receipt", record.broker_receipt_status)}
            </div>
            <div class="trade-lifecycle-links">${references}</div>
            <p class="mini">${htmlText(record.boundary)}</p>
        </article>
    `;
}

function renderProofPartitionCard(partition, tone = "pending") {
    return `
        <article class="trade-proof-partition ${statusClass(tone)}">
            <span>${htmlText(partition.label)}</span>
            <strong>${htmlText(partition.record_count)} records</strong>
            <div class="summary-strip compact">
                ${Object.entries(partition)
                    .filter(([key]) => !["label", "record_count"].includes(key))
                    .map(([key, value]) => renderMetric(key.replaceAll("_", " "), typeof value === "boolean" ? (value ? "yes" : "no") : value))
                    .join("")}
            </div>
        </article>
    `;
}

function renderTradeLifecycleWorkspace(model) {
    const records = asArray(model.lifecycle_records);
    return `
        <section class="trades-workspace" data-trades-workspace>
            <div class="trades-workspace-head">
                <div>
                    <p class="label">Trades workspace</p>
                    <h3>Trade lifecycle board</h3>
                    <p>${htmlText(model.summary)} ${htmlText(model.boundary)} A trade idea is not an order.</p>
                </div>
                <div class="trade-lifecycle-safety">
                    <strong>Verified performance only</strong>
                    <span>Test trades stay separate from verified paper-trading performance.</span>
                </div>
            </div>
            <div class="trade-lifecycle-filters" data-trade-lifecycle-filters>
                ${asArray(model.lifecycle_filters).map((filter, index) => renderTradesWorkspaceFilter(filter, index === 0)).join("")}
            </div>
            <div class="trade-lifecycle-strip">
                ${asArray(model.lifecycle).map((item, index) => `
                    <article class="${statusClass(item.tone)}">
                        <span>${String(index + 1).padStart(2, "0")}</span>
                        <strong>${htmlText(item.label)}</strong>
                        <em>${htmlText(item.count)}</em>
                    </article>
                `).join("")}
            </div>
            <div class="trade-proof-partitions">
                ${renderProofPartitionCard(model.proof_partitions.phase5_test_lifecycle, "pending")}
                ${renderProofPartitionCard(model.proof_partitions.phase7_demo_proof, model.proof_credit.display_allowed ? "online" : "pending")}
            </div>
            <div class="trade-evidence-links">
                <a href="${htmlText(model.evidence_links.source_quorum.href)}"><strong>Source quorum</strong><span>${htmlText(model.evidence_links.source_quorum.status)}</span></a>
                <a href="${htmlText(model.evidence_links.risk_decision.href)}"><strong>Risk decision</strong><span>${htmlText(model.evidence_links.risk_decision.status)}</span></a>
                <a href="${htmlText(model.evidence_links.broker_receipt.href)}"><strong>Broker receipt</strong><span>${htmlText(model.evidence_links.broker_receipt.status)}</span></a>
            </div>
            <div class="trade-lifecycle-grid" data-trade-lifecycle-grid>
                ${records.length ? records.map(renderTradeLifecycleCard).join("") : `
                    <article class="trade-lifecycle-card pending" data-trade-lifecycle-card data-filter-states="all">
                        <h3>No trade lifecycle records</h3>
                        <p>Qadam has no observed signal, candidate, paper order, position, closed trade, or postmortem in this status snapshot.</p>
                    </article>
                `}
            </div>
        </section>
    `;
}

function initTradeLifecycleFilters(root) {
    if (!root || typeof root.querySelectorAll !== "function") return;
    const buttons = Array.from(root.querySelectorAll("[data-trade-lifecycle-filter]"));
    const cards = Array.from(root.querySelectorAll("[data-trade-lifecycle-card]"));
    if (!buttons.length || !cards.length) return;
    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            const filter = button.dataset.tradeLifecycleFilter || "all";
            buttons.forEach((option) => {
                option.setAttribute("aria-pressed", option === button ? "true" : "false");
            });
            cards.forEach((card) => {
                const states = String(card.dataset.filterStates || "all").split(/\s+/);
                const visible = filter === "all" || states.includes(filter);
                card.hidden = !visible;
                card.setAttribute("aria-hidden", visible ? "false" : "true");
            });
        });
    });
}

function renderPhase4Strategy(status) {
    const phase4 = phase4StrategyStatus(status);
    const summary = dashboardQuery("[data-phase4-summary]");
    const target = dashboardQuery("[data-phase4-strategy]");
    const approval = phase4.approval_event || {};
    const certification = phase4.certification || {};
    const preferenceGate = certification.preference_mcp_certification_gate || {};
    const strategyDocument = phase4.strategy_document || {};
    const toggleSummary = phase4.strategy_toggles || {};
    const marketPolicy = phase4.market_confirmation_policy || {};
    const approvalState = phase4.approval_event_status || approval.approval_state || "missing";
    const approvalTone = phase4ApprovalTone(phase4);
    const toggleCount = phase4.toggle_count || toggleSummary.toggle_count || 0;
    const draftToggleCount = toggleSummary.draft_toggle_count || 0;
    const approvedShadowCount = phase4ApprovedShadowCount(phase4);
    const blockedByApproval = !phase4.phase4_certification_allowed;
    const executionBoundary = phase4.no_execution_boundary || phase4.boundary || (
        "Phase 4 strategy visibility is governance-only and non-executable."
    );

    if (summary) {
        summary.innerHTML = [
            renderMetric("Phase", phase4.phase || "Q4"),
            renderMetric("Stage", phase4.stage || "Q4-11"),
            renderMetric("Document", phase4.strategy_document_status || "missing"),
            renderMetric("Approval", approvalState),
            renderMetric("Toggles", `${toggleCount} visible`),
            renderMetric("Approved-shadow", approvedShadowCount),
            renderMetric("Certification", phase4.phase4_certified ? "Certified" : (phase4.phase4_certification_allowed ? "Allowed" : "Blocked")),
            renderMetric("Execution", phase4.execution_allowed_count ? "Unexpected" : "Blocked")
        ].join("");
    }

    if (!target) return;

    const amendmentHtml = asArray(approval.required_amendments).length
        ? asArray(approval.required_amendments).map((item) => `
            <li>
                <strong>Required amendment</strong>
                <span>${htmlText(item)}</span>
            </li>
        `).join("")
        : `
            <li>
                <strong>No amendments recorded</strong>
                <span>Explicit approval remains required before certification can pass.</span>
            </li>
        `;

    const blockerHtml = asArray(certification.certification_blockers).length
        ? asArray(certification.certification_blockers).map((item) => `
            <li>
                <strong>Certification blocker</strong>
                <span>${htmlText(item)}</span>
            </li>
        `).join("")
        : `
            <li>
                <strong>No certification blockers exported</strong>
                <span>Phase 4 certification has not produced a blocker list in this snapshot.</span>
            </li>
        `;

    const nextStepHtml = asArray(certification.required_next_steps).length
        ? asArray(certification.required_next_steps).map((item) => `
            <li>
                <strong>Required next step</strong>
                <span>${htmlText(item)}</span>
            </li>
        `).join("")
        : "";

    const toggleHtml = asArray(toggleSummary.toggles).length
        ? asArray(toggleSummary.toggles).map((toggle) => `
            <article class="cognition-card strategy-toggle-card">
                <div class="cognition-card-head">
                    ${renderStatusPill(toggle.toggle_state || "draft")}
                    <p class="label">${htmlText(toggle.strategy_key, "strategy family")}</p>
                </div>
                <h3>${htmlText(toggle.label, "Strategy family")}</h3>
                <p>${htmlText(toggle.boundary, "Strategy toggle visibility only; it cannot route execution.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(toggle.visible_in_cockpit ? "visible to Fund Manager" : "not visible", toggle.visible_in_cockpit ? "pending" : "blocked")}
                    ${renderInlineBadge(`approval ${dashboardText(toggle.approval_state || approvalState)}`, approvalTone)}
                    ${renderInlineBadge(toggle.execution_allowed ? "execution allowed" : "no execution", toggle.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(toggle.paper_order_allowed ? "paper order allowed" : "no paper order", toggle.paper_order_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(toggle.broker_write_allowed ? "broker write" : "no broker write", toggle.broker_write_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(toggle.live_capital_enabled ? "live capital" : "live capital disabled", toggle.live_capital_enabled ? "blocked" : "online")}
                </div>
            </article>
        `).join("")
        : `
            <article class="cognition-card strategy-toggle-card">
                <h3>No strategy toggles exported</h3>
                <p>The dashboard has no strategy toggle records in this snapshot.</p>
            </article>
        `;

    target.innerHTML = `
        ${renderPanelBrief({
            id: "phase4_strategy",
            question: "Is Phase 4 visible but non-executable?",
            state: dashboardText(approvalState),
            tone: approvalTone,
            primary: `Phase 4 is at ${dashboardText(phase4.stage || "Q4-11")} with document ${dashboardText(phase4.strategy_document_status, "missing")}, ${toggleCount} visible strategy toggles, and ${approvedShadowCount} approved-shadow toggles.`,
            secondary: blockedByApproval
                ? "Explicit Fund Manager approval is still blocking Phase 4 certification."
                : "Approved strategy visibility is present; execution boundaries must still hold.",
            boundary: `No execution. ${executionBoundary}`
        })}
        <section class="cognition-section">
            <p class="label">Audit and document state</p>
            <div class="summary-strip compact">
                ${renderMetric("Latest audit", phase4.audit_completion_state?.latest_completed_stage || "not exported")}
                ${renderMetric("Current stage", phase4.audit_completion_state?.current_stage || phase4.stage || "Q4-11")}
                ${renderMetric("Completed", phase4.audit_completion_state?.completed_stage_count || 0)}
                ${renderMetric("Strategy families", strategyDocument.strategy_family_candidate_count || toggleCount)}
                ${renderMetric("Active instruments", strategyDocument.active_instrument_count || 0)}
                ${renderMetric("Fingerprint", shortFingerprint(strategyDocument.document_fingerprint))}
                ${renderMetric("Doc validation", strategyDocument.validation_error_count || 0)}
                ${renderMetric("Approval validation", approval.validation_error_count || 0)}
            </div>
        </section>
        <section class="cognition-section">
            <p class="label">Approval gate</p>
            <div class="summary-strip compact">
                ${renderMetric("State", approvalState)}
                ${renderMetric("Logged", approval.approval_logged ? "Yes" : "No")}
                ${renderMetric("Approver", approval.approver_label || "pending")}
                ${renderMetric("Required amendments", approval.required_amendment_count || 0)}
                ${renderMetric("Certification", phase4.phase4_certification_allowed ? "Allowed" : "Blocked")}
                ${renderMetric("Event correlation", approval.event_log_correlation_present ? "Present" : "Missing")}
            </div>
            <ul class="status-list">${amendmentHtml}</ul>
        </section>
        <section class="cognition-section">
            <p class="label">Certification gate</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", certification.status || phase4.certification_status || "not run")}
                ${renderMetric("Logged", certification.certification_logged ? "Yes" : "No")}
                ${renderMetric("Phase 4", certification.phase4_certified ? "Certified" : "Blocked")}
                ${renderMetric("Phase 5", certification.phase5_handoff_allowed ? "Allowed" : "Blocked")}
                ${renderMetric("Blockers", certification.certification_blocker_count || 0)}
                ${renderMetric("Validation errors", certification.validation_error_count || 0)}
                ${renderMetric("Preference sources", preferenceGate.source_promotion_status || "not run")}
                ${renderMetric("Promoted", preferenceGate.source_promotion_promoted_decision_count || 0)}
                ${renderMetric("Source count", preferenceGate.source_promotion_canonical_source_count_after || 0)}
            </div>
            <ul class="status-list">${blockerHtml}${nextStepHtml}</ul>
        </section>
        <section class="cognition-section">
            <p class="label">Strategy toggles</p>
            <div class="summary-strip compact">
                ${renderMetric("Visible", toggleSummary.visible_toggle_count || toggleCount)}
                ${renderMetric("Draft", draftToggleCount)}
                ${renderMetric("Approved-shadow", approvedShadowCount)}
                ${renderMetric("Inactive", toggleSummary.inactive_toggle_count || 0)}
                ${renderMetric("Validation errors", toggleSummary.validation_error_count || 0)}
                ${renderMetric("Event Log", toggleSummary.event_log_required ? "Required" : "Missing")}
            </div>
            <div class="hypothesis-stack">${toggleHtml}</div>
        </section>
        <section class="cognition-section">
            <p class="label">Capability boundary</p>
            <div class="tag-row">
                ${renderInlineBadge("No execution", phase4.execution_allowed_count ? "blocked" : "online")}
                ${renderInlineBadge("No paper orders", phase4.paper_order_allowed_count ? "blocked" : "online")}
                ${renderInlineBadge("No broker writes", phase4.broker_write_allowed_count ? "blocked" : "online")}
                ${renderInlineBadge("Live capital disabled", phase4.live_capital_enabled_count ? "blocked" : "online")}
                ${renderInlineBadge("Yahoo Finance supplemental", "pending")}
                ${renderInlineBadge("Preference zero promoted sources", preferenceGate.source_promotion_promoted_decision_count ? "blocked" : "online")}
                ${renderInlineBadge(preferenceGate.preference_mcp_source_36 ? "Preference source 36" : "Preference not source 36", preferenceGate.preference_mcp_source_36 ? "blocked" : "online")}
                ${renderInlineBadge(marketPolicy.yahoo_finance_role || "supplemental market confirmation only", "pending")}
            </div>
            <p class="mini">${htmlText(executionBoundary)}</p>
        </section>
    `;
}

function renderWatching(status, viewModels = {}) {
    const watching = asArray(status.watching);
    const pipelineSummary = asArray(status.source_pipeline_summary);
    const sourcesModel = viewModels?.sources_model || buildSourcesModel(status);
    const yahooFinance = status.yahoo_finance || {};
    const preferenceMcp = status.preference_mcp || {};
    const summaryByPipeline = new Map(pipelineSummary.map((pipeline) => [pipeline.pipeline, pipeline]));
    const degraded = Number(sourcesModel.counts?.degraded || 0);
    const pending = Number(sourcesModel.counts?.pending || 0);
    const missingCredentialCount = Number(sourcesModel.counts?.missing_credentials || 0);
    const optionalCredentialCount = Number(sourcesModel.counts?.optional_credentials || 0);
    replacePanelBrief("watching", {
        question: "Are Qadam's inputs healthy enough to trust?",
        state: `${sourcesModel.counts?.core_ok || 0}/${sourcesModel.counts?.core || 0} core OK`,
        tone: degraded || missingCredentialCount ? "degraded" : "online",
        primary: `${watching.length} watched sources across ${pipelineSummary.length} pipelines. Required issues: ${degraded} need attention, ${missingCredentialCount} not configured. Optional feeds not configured: ${optionalCredentialCount}.`,
        secondary: "Stale heartbeats, missing credentials, degraded feeds, local-only sources, and whether a source can influence signals.",
        boundary: "Sources create observations only. Optional source gaps do not block the paper-trading core."
    });
    const workspace = dashboardQuery("[data-sources-workspace-slot]");
    if (workspace) {
        workspace.innerHTML = renderSourcesWorkspace(sourcesModel);
    }
    const summary = dashboardQuery("[data-source-summary]");
    if (summary) {
        const history = asArray(status.source_heartbeat_history);
        const lastRun = history[history.length - 1];
        summary.innerHTML = [
            sourceSummary(status),
            renderMetric("Pipelines", pipelineSummary.length),
            renderMetric("Adapters", watching.filter((source) => source.promoted_adapter).length),
            renderMetric("Yahoo Finance", yahooFinance.status || "not exported"),
            renderMetric("Preference MCP", preferenceMcp.status || "not exported"),
            renderMetric("Last heartbeat", formatTime(lastRun?.checked_at || status.generated_at))
        ].join("");
    }

    const grouped = watching.reduce((acc, source) => {
        const pipeline = source.pipeline || "unknown";
        acc[pipeline] = acc[pipeline] || [];
        acc[pipeline].push(source);
        return acc;
    }, {});

    const target = dashboardQuery("[data-watching-list]");
    if (!target) return;

    if (!watching.length) {
        target.innerHTML = `
            <article class="empty-state">
                <h3>Not connected yet</h3>
                <p>No watched-source records have been exported into this snapshot.</p>
            </article>
        `;
        return;
    }

    const yahooFinanceHtml = yahooFinance.source
        ? `
            <details class="pipeline-row supplemental-market-confirmation" open>
                <summary>
                    <h3>Supplemental market confirmation</h3>
                    <p>Yahoo Finance ${htmlText(yahooFinance.status, "not exported")} · ${htmlText(yahooFinance.market_confirmation_role, "supplemental")} · ${dashboardText(yahooFinance.symbol_allowlist_count, "0")} symbols · no signal, order, broker, fill, receipt, or reconciliation authority</p>
                </summary>
                <ul class="source-table">
                    <li class="source-row">
                        <div class="source-main">
                            ${renderStatusPill(yahooFinance.degraded ? "degraded" : "online")}
                            <div>
                                <strong>Yahoo Finance</strong>
                                <span>${htmlText(yahooFinance.classification)} · ${htmlText(yahooFinance.market_confirmation_policy)}</span>
                            </div>
                        </div>
                        <div class="source-meta">
                            ${renderInlineBadge(yahooFinance.live_read_enabled ? "live read enabled" : "live read deferred", yahooFinance.live_read_enabled ? "online" : "pending")}
                            ${renderInlineBadge(yahooFinance.sample_mode_available ? "sample mode" : "no sample mode", yahooFinance.sample_mode_available ? "online" : "degraded")}
                            ${renderInlineBadge(yahooFinance.canonical_source ? "canonical source" : "not canonical", yahooFinance.canonical_source ? "degraded" : "online")}
                            ${renderInlineBadge(yahooFinance.raw_payload_exposed ? "raw payload exposed" : "raw payload hidden", yahooFinance.raw_payload_exposed ? "degraded" : "online")}
                            ${renderInlineBadge(yahooFinance.signal_authority ? "signal authority" : "no signal authority", yahooFinance.signal_authority ? "degraded" : "online")}
                            ${renderInlineBadge(yahooFinance.order_authority ? "order authority" : "no order authority", yahooFinance.order_authority ? "degraded" : "online")}
                            ${renderInlineBadge(yahooFinance.reconciliation_truth_authority ? "reconciliation truth" : "no reconciliation truth", yahooFinance.reconciliation_truth_authority ? "degraded" : "online")}
                            ${renderInlineBadge(formatTime(yahooFinance.last_check_at), yahooFinance.status)}
                        </div>
                        <p>${htmlText(yahooFinance.degraded_reason || yahooFinance.status)} · ${htmlText(yahooFinance.boundary, "Read-only supplemental market confirmation.")}</p>
                    </li>
                </ul>
            </details>
        `
        : "";

    const preferenceDomainPacks = asArray(preferenceMcp.approved_domain_packs);
    const preferenceMcpHtml = preferenceMcp.source_key
        ? `
            <details class="pipeline-row supplemental-data-plane" open>
                <summary>
                    <h3>Preference MCP data plane</h3>
                    <p>${htmlText(preferenceMcp.status, "not exported")} · identity ${htmlText(preferenceMcp.identity_status, "not verified")} · quota ${htmlText(preferenceMcp.quota_status, "unknown")} · ${dashboardText(preferenceMcp.approved_domain_pack_count, "0")} domain packs · no source-quorum, trade, broker, paid-tool, or live-capital authority</p>
                </summary>
                <ul class="source-table">
                    <li class="source-row">
                        <div class="source-main">
                            ${renderStatusPill(preferenceMcp.degraded ? "degraded" : "online")}
                            <div>
                                <strong>Preference / PREF MCP</strong>
                                <span>${htmlText(preferenceMcp.classification)} · ${htmlText(preferenceMcp.provider_label)}</span>
                            </div>
                        </div>
                        <div class="source-meta">
                            ${renderInlineBadge(preferenceMcp.enabled ? "live MCP enabled" : "live MCP disabled", preferenceMcp.enabled ? "pending" : "blocked")}
                            ${renderInlineBadge(`identity ${dashboardText(preferenceMcp.identity_gate_status, "blocked")}`, preferenceMcp.identity_gate_status)}
                            ${renderInlineBadge(`quota ${dashboardText(preferenceMcp.quota_status, "unknown")}`, preferenceMcp.quota_degraded ? "degraded" : "online")}
                            ${renderInlineBadge(`catalog ${dashboardText(preferenceMcp.catalog_status, "not run")}`, preferenceMcp.catalog_status)}
                            ${renderInlineBadge(`provenance ${dashboardText(preferenceMcp.provenance_status, "not run")}`, preferenceMcp.provenance_status)}
                            ${renderInlineBadge(`shadow ${dashboardText(preferenceMcp.shadow_context_status, "not run")}`, preferenceMcp.shadow_context_status)}
                            ${renderInlineBadge(`blocked paid tools ${dashboardText(preferenceMcp.blocked_paid_tool_count, "0")}`, preferenceMcp.blocked_paid_tool_count ? "blocked" : "online")}
                            ${renderInlineBadge(preferenceMcp.raw_payload_exposed ? "raw payload exposed" : "raw payload hidden", preferenceMcp.raw_payload_exposed ? "degraded" : "online")}
                            ${renderInlineBadge(preferenceMcp.trade_candidate_creation_allowed ? "trade authority" : "no trade authority", preferenceMcp.trade_candidate_creation_allowed ? "degraded" : "online")}
                            ${renderInlineBadge(preferenceMcp.broker_write_allowed ? "broker writes" : "no broker writes", preferenceMcp.broker_write_allowed ? "degraded" : "online")}
                            ${renderInlineBadge(preferenceMcp.live_capital_enabled ? "live capital" : "live capital disabled", preferenceMcp.live_capital_enabled ? "degraded" : "online")}
                        </div>
                        <div class="mission-mini-grid compact">
                            ${renderMetric("Data-plane status", preferenceMcp.status || "not exported")}
                            ${renderMetric("Domain-pack coverage", `${preferenceMcp.approved_domain_pack_count || 0} approved`)}
                            ${renderMetric("Provenance health", `${preferenceMcp.provenance_context_status || "not run"} · ${preferenceMcp.provenance_distinct_upstream_source_count || 0} upstream`)}
                            ${renderMetric("Quota/credit health", `${preferenceMcp.quota_status || "unknown"} · ${preferenceMcp.daily_call_budget || 0}/${preferenceMcp.run_call_budget || 0}`)}
                            ${renderMetric("Blocked paid tools", preferenceMcp.blocked_paid_tool_count || 0)}
                            ${renderMetric("Shadow challenges", preferenceMcp.active_required_challenge_count || 0)}
                        </div>
                        <div class="source-meta">
                            ${preferenceDomainPacks.length
        ? preferenceDomainPacks.map((domainPack) => renderInlineBadge(domainPack, "pending")).join("")
        : renderInlineBadge("domain packs not exported", "pending")}
                        </div>
                        <p>${htmlText(preferenceMcp.degraded_reason || preferenceMcp.status)} · ${htmlText(preferenceMcp.boundary, "Public-safe read-only supplemental data plane.")}</p>
                    </li>
                </ul>
            </details>
        `
        : "";

    const sourceLedgerHtml = yahooFinanceHtml + preferenceMcpHtml + Object.entries(grouped)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([pipeline, sources], index) => {
            const counts = countBy(sources, "status");
            const pipelineCounts = summaryByPipeline.get(pipeline) || {};
            const missingCredentials = sources.filter((source) => source.credential_status === "missing").length;
            const adapterReady = sources.filter((source) => source.promoted_adapter).length;
            const signalReady = sources.filter((source) => source.can_influence_signals).length;
            const localOnly = pipelineCounts.local_only_count || counts.local_only || counts["local-only"] || 0;
            const rows = sources
                .sort((a, b) => String(a.source_name).localeCompare(String(b.source_name)))
                .map((source) => `
                    <li class="source-row">
                        <div class="source-main">
                            ${renderStatusPill(sourceDisplayStatus(source))}
                            <div>
                                <strong>${htmlText(source.source_name, source.source_key)}</strong>
                                <span>${htmlText(source.readiness)} · tier ${htmlText(source.tier)} · ${htmlText(source.cadence, "cadence unknown")}</span>
                            </div>
                        </div>
                        <div class="source-meta">
                            ${renderInlineBadge(source.credential_status, source.credential_status === "missing" && sourceIsCore(source) ? "degraded" : "optional")}
                            ${renderInlineBadge(source.promoted_adapter ? "adapter" : "registry", source.promoted_adapter ? "online" : "pending")}
                            ${renderInlineBadge(source.auth_class, source.auth_class === "credential_required" && sourceIsCore(source) ? "degraded" : "optional")}
                            ${renderInlineBadge(source.registry_status, "pending")}
                            ${renderInlineBadge(`${dashboardText(source.endpoint_count, "0")} endpoints`, source.endpoint_count ? "online" : "pending")}
                            ${renderInlineBadge(`trust ${dashboardText(source.trust_score, "n/a")}`, source.trust_score ? "online" : "pending")}
                            ${renderInlineBadge(source.can_influence_signals ? "can influence signals" : "evidence only", source.can_influence_signals ? "online" : "optional")}
                            ${renderInlineBadge(`payload ${formatTime(source.last_payload_time)}`, source.last_payload_time ? "online" : "pending")}
                            ${renderInlineBadge(`latency ${formatLatency(source.latency_ms)}`, source.latency_ms ? "online" : "pending")}
                            ${renderInlineBadge(formatTime(source.last_heartbeat), sourceDisplayStatus(source))}
                        </div>
                        <p>${htmlText(source.degraded_reason || source.raw_status)} · ${htmlText(source.influence_boundary, "blocked until signal integrity gate")}</p>
                    </li>
                `)
                .join("");
            return `
                <details class="pipeline-row" ${index === 0 ? "open" : ""}>
                    <summary>
                        <h3>${htmlText(pipeline)}</h3>
                        <p>${sources.length} sources · ${counts.online || 0} online · ${counts.degraded || 0} degraded · ${counts.pending || 0} pending · ${localOnly} local-only · ${missingCredentials} credentials missing · ${adapterReady} adapters · ${signalReady} signal-influencing</p>
                    </summary>
                    <ul class="source-table">${rows}</ul>
                </details>
            `;
        })
        .join("");
    target.innerHTML = `
        <details class="evidence-source-ledger" data-evidence-source-ledger>
            <summary>
                <strong>Detailed source ledger</strong>
                <span>Advanced diagnostic rows for credentials, heartbeats, adapters, source payload freshness, and supplemental inputs.</span>
            </summary>
            <div class="evidence-source-ledger-body">${sourceLedgerHtml}</div>
        </details>
    `;
}

function renderReasoningLaneCard(lane) {
    return `
        <article class="reasoning-lane-card ${statusClass(lane.status)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(lane.status || "pending")}
                <p class="label">${htmlText(lane.watch, "review")}</p>
            </div>
            <h3>${htmlText(lane.label, "Reasoning step")}</h3>
            <p>${htmlText(lane.summary, "No reasoning summary exported.")}</p>
            <small>${htmlText(lane.boundary, "Read-only reasoning state.")}</small>
        </article>
    `;
}

function renderWorldviewPriorSummary(prior) {
    const lenses = asArray(prior.active_lenses);
    const priorCards = lenses.length
        ? lenses.slice(0, 3).map((lens) => `
            <article class="reasoning-prior-card">
                <p class="label">${htmlText(lens.claim_type, "worldview prior")}</p>
                <h3>${htmlText(lens.key, "private prior")}</h3>
                <p>${htmlText(lens.claim, "No prior claim exported.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge("Prior, not evidence", "blocked")}
                    ${renderInlineBadge(lens.corroboration_status || "prior only", "pending")}
                    ${renderInlineBadge(`${asArray(lens.live_sources_to_check).length} checks`, "pending")}
                    ${renderInlineBadge(`${asArray(lens.market_channels).length} channels`, "pending")}
                </div>
                <dl class="cognition-facts">
                    <div>
                        <dt>Observable</dt>
                        <dd>${htmlText(asArray(lens.observable_signatures).join(", "), "No observable signatures exported.")}</dd>
                    </div>
                    <div>
                        <dt>Boundary</dt>
                        <dd>${htmlText(lens.evidence_boundary, "Prior, not evidence.")}</dd>
                    </div>
                </dl>
            </article>
        `).join("")
        : `<article class="reasoning-prior-card"><h3>No worldview priors exported</h3><p>Reasoning can still show evidence and blockers without private-prior cards.</p></article>`;
    const decisionChain = asArray(prior.decision_chain).length
        ? asArray(prior.decision_chain)
        : ["private worldview prior", "observable signature", "live-source corroboration", "trade gates"];
    return `
        <section class="reasoning-section">
            <div class="reasoning-section-head">
                <div>
                    <p class="label">Worldview prior</p>
                    <h3>Question generator, not proof</h3>
                </div>
                ${renderInlineBadge("Prior, not evidence", "blocked")}
            </div>
            <p>${htmlText(prior.trading_philosophy, "Qadam uses priors to ask better questions, not as evidence.")}</p>
            <ol class="reasoning-chain-list">
                ${decisionChain.map((step) => `<li>${htmlText(step)}</li>`).join("")}
            </ol>
            <div class="reasoning-prior-grid">${priorCards}</div>
        </section>
    `;
}

function renderReasoningHypothesisSummary(hypothesis) {
    return `
        <article class="reasoning-hypothesis-card ${statusClass(hypothesis.advancement_state)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(hypothesis.status || "shadow_only")}
                <p class="label">${htmlText(hypothesis.instrument_focus, "instrument watchlist")}</p>
            </div>
            <h3>${htmlText(hypothesis.title, "Shadow hypothesis")}</h3>
            <p>${htmlText(hypothesis.thesis, "No thesis exported.")}</p>
            <div class="tag-row">
                ${renderInlineBadge("Hypothesis, not trade idea", "blocked")}
                ${renderInlineBadge("No paper/order authority", "online")}
                ${renderInlineBadge(`state ${dashboardText(hypothesis.advancement_state, "blocked")}`, "blocked")}
                ${renderInlineBadge(`packet ${dashboardText(hypothesis.evidence_packet_id, "not linked")}`, hypothesis.evidence_packet_id === "not linked" ? "pending" : "online")}
            </div>
            <dl class="cognition-facts">
                <div>
                    <dt>Advanced by</dt>
                    <dd>${htmlText(hypothesis.advanced_by, "No advancement reason exported.")}</dd>
                </div>
                <div>
                    <dt>Stalled by</dt>
                    <dd>${htmlText(hypothesis.stalled_by, "No stall reason exported.")}</dd>
                </div>
                <div>
                    <dt>Blocked by</dt>
                    <dd>${htmlText(hypothesis.blocked_reason, "trade layer not reached")}</dd>
                </div>
                <div>
                    <dt>Missing</dt>
                    <dd class="tag-row">${renderTagList(hypothesis.missing_corroboration, "No missing corroboration recorded")}</dd>
                </div>
                <div>
                    <dt>Boundary</dt>
                    <dd>${htmlText(hypothesis.boundary, "Hypothesis only.")}</dd>
                </div>
            </dl>
        </article>
    `;
}

function renderReasoningResearchGoalSummary(goal) {
    return `
        <article class="reasoning-hypothesis-card ${statusClass(goal.status)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(goal.status || "needs_evidence")}
                <p class="label">${htmlText(goal.market_channel, "market channel")}</p>
            </div>
            <h3>${htmlText(goal.goal_id, "Research Goal")}</h3>
            <p>${htmlText(goal.hypothesis, "No research hypothesis exported.")}</p>
            <div class="tag-row">
                ${renderInlineBadge("Pre-signal research", "pending")}
                ${renderInlineBadge("Not a trade candidate", "blocked")}
                ${renderInlineBadge("No paper/order authority", "online")}
                ${renderInlineBadge(`quorum ${dashboardText(goal.minimum_source_quorum, "2")} sources`, "pending")}
            </div>
            <dl class="cognition-facts">
                <div>
                    <dt>Watching</dt>
                    <dd class="tag-row">${renderTagList(goal.watched_instruments, "No instruments exported")}</dd>
                </div>
                <div>
                    <dt>Required sources</dt>
                    <dd class="tag-row">${renderTagList(goal.required_sources, "No source requirements exported")}</dd>
                </div>
                <div>
                    <dt>Private lens</dt>
                    <dd>${htmlText(goal.worldview_lens, "private prior only")} · ${htmlText(goal.akber_stage, "Akber stage not exported")}</dd>
                </div>
                <div>
                    <dt>Missing</dt>
                    <dd class="tag-row">${renderTagList(goal.missing_corroboration, "No missing corroboration exported")}</dd>
                </div>
                <div>
                    <dt>Next handoff</dt>
                    <dd>${htmlText(goal.owner_agent, "research analyst")} -> ${htmlText(goal.next_handoff, "local research compression")}</dd>
                </div>
                <div>
                    <dt>Boundary</dt>
                    <dd>${htmlText(goal.boundary, "Research Goal is pre-signal only.")}</dd>
                </div>
            </dl>
        </article>
    `;
}

function renderReasoningEvidenceSummary(packet) {
    const itemHtml = asArray(packet.items).length
        ? asArray(packet.items).map((item) => `
            <li>
                <strong>${htmlText(item.source, "evidence source")}</strong>
                <span>${htmlText(item.event_type, "event")} · trust ${dashboardText(item.trust_score, "n/a")}</span>
                <small>${htmlText(item.summary, "No summary.")}</small>
            </li>
        `).join("")
        : `<li><strong>No evidence items</strong><span>Waiting for source observations.</span></li>`;
    return `
        <article class="reasoning-evidence-card">
            <div class="source-workspace-topline">
                ${renderStatusPill(packet.source_count ? "online" : "pending")}
                <p class="label">${htmlText(packet.signal_id, "unlinked signal")}</p>
            </div>
            <h3>${htmlText(packet.trail_id, "Evidence packet")}</h3>
            <div class="summary-strip compact">
                ${renderMetric("Sources", packet.source_count || 0)}
                ${renderMetric("Items", packet.item_count || 0)}
                ${renderMetric("Avg trust", dashboardText(packet.average_trust_score, "n/a"))}
                ${renderMetric("Min trust", dashboardText(packet.min_trust_score, "n/a"))}
            </div>
            <dl class="cognition-facts">
                <div>
                    <dt>Sources</dt>
                    <dd>${htmlText(asArray(packet.sources).join(", "), "No sources recorded")}</dd>
                </div>
                <div>
                    <dt>Boundary</dt>
                    <dd>${htmlText(packet.boundary, "Evidence supports review only.")}</dd>
                </div>
            </dl>
            <ul class="status-list reasoning-evidence-items">${itemHtml}</ul>
        </article>
    `;
}

function renderMissingCorroborationCard(item) {
    return `
        <article class="reasoning-missing-card ${statusClass(item.status)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(item.status || "pending")}
                <p class="label">Missing corroboration</p>
            </div>
            <h3>${htmlText(item.label, "Missing evidence")}</h3>
            <p>${htmlText(item.why_it_matters, "Qadam holds the idea until this is resolved.")}</p>
            <small>${htmlText(item.boundary, "Normal blocker.")}</small>
        </article>
    `;
}

function renderReasoningReviewCard(review) {
    return `
        <article class="reasoning-review-card ${statusClass(review.status)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(review.status || "pending")}
                <p class="label">${htmlText(review.role, "reviewer")}</p>
            </div>
            <h3>${htmlText(review.label, "Review")}</h3>
            <p>${htmlText(review.summary, "No review summary exported.")}</p>
            <div class="tag-row">
                ${renderInlineBadge(`focus ${dashboardText(review.focus, "none")}`, review.focus ? "pending" : "neutral")}
                ${renderInlineBadge(review.can_advance_trade ? "can advance trade" : "challenge-only", review.can_advance_trade ? "blocked" : "online")}
                ${renderInlineBadge("No paper/order authority", "online")}
            </div>
            <section class="trade-check-section">
                <p class="label">Challenge list</p>
                <div class="tag-row">${renderTagList(review.missing_corroboration, "No challenge list exported")}</div>
            </section>
            <small>${htmlText(review.boundary, "Review-only boundary.")}</small>
        </article>
    `;
}

function renderQuantAnnotationCard(annotation) {
    return `
        <article class="reasoning-quant-card ${statusClass(annotation.status)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(annotation.status || "pending")}
                <p class="label">Head of Quant annotation</p>
            </div>
            <h3>Quant/quantum annotation</h3>
            <p>${htmlText(annotation.boundary, "Head of Quant output is a shadow annotation only.")}</p>
            <div class="summary-strip compact">
                ${renderMetric("Backend", annotation.backend || "classical fallback")}
                ${renderMetric("Recommendation", annotation.recommendation || "hold")}
                ${renderMetric("Route", annotation.route_type || "shadow annotation")}
                ${renderMetric("Target", annotation.annotation_target || "reviewed context")}
                ${renderMetric("Hardware jobs", annotation.hardware_submitted_count || 0)}
                ${renderMetric("Candidates", annotation.trade_candidate_created_count || 0)}
                ${renderMetric("Fire Opal IBM", annotation.fire_opal_ibm_status || "not exported")}
                ${renderMetric("IBM blocker", annotation.fire_opal_ibm_blocker || "not exported")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(annotation.fire_opal_access_verified ? "Fire Opal verified" : "Fire Opal pending", annotation.fire_opal_access_verified ? "online" : "blocked")}
                ${renderInlineBadge(annotation.qiskit_runtime_ready ? "IBM runtime installed" : "IBM runtime missing", annotation.qiskit_runtime_ready ? "online" : "blocked")}
                ${renderInlineBadge(annotation.ibm_credentials_configured ? "IBM credentials configured" : "IBM credentials missing", annotation.ibm_credentials_configured ? "online" : "blocked")}
                ${renderInlineBadge(annotation.hardware_submission_allowed ? "hardware submission allowed" : "hardware submission blocked", annotation.hardware_submission_allowed ? "blocked" : "online")}
                ${renderInlineBadge(annotation.execution_allowed ? "execution allowed" : "execution blocked", annotation.execution_allowed ? "blocked" : "online")}
                ${renderInlineBadge(annotation.paper_order_allowed ? "paper order allowed" : "paper order blocked", annotation.paper_order_allowed ? "blocked" : "online")}
                ${renderInlineBadge("Shadow annotation", "pending")}
            </div>
        </article>
    `;
}

function renderReasoningReviewGroup(group, bodyHtml, open = false) {
    return `
        <details class="reasoning-review-group" ${open ? "open" : ""} data-reasoning-review-group="${literalHtmlText(group.id)}">
            <summary>
                <strong>${htmlText(group.label)}</strong>
                <span>${htmlText(group.summary)}</span>
                <em>${htmlText(group.record_count)} records</em>
            </summary>
            <div class="reasoning-review-group-body">${bodyHtml}</div>
        </details>
    `;
}

function renderReasoningWorkspace(model) {
    const lanesHtml = asArray(model.lanes).map(renderReasoningLaneCard).join("");
    const researchGoalHtml = asArray(model.research_goal_queue).length
        ? asArray(model.research_goal_queue).map(renderReasoningResearchGoalSummary).join("")
        : `<article class="reasoning-hypothesis-card"><h3>No research goals visible</h3><p>Research goals appear before hypotheses when source observations create a watch question.</p></article>`;
    const hypothesesHtml = asArray(model.hypothesis_queue).length
        ? asArray(model.hypothesis_queue).map(renderReasoningHypothesisSummary).join("")
        : `<article class="reasoning-hypothesis-card"><h3>No hypotheses visible</h3><p>Qadam has no hypotheses in this snapshot.</p></article>`;
    const evidenceHtml = asArray(model.evidence_packets).length
        ? asArray(model.evidence_packets).map(renderReasoningEvidenceSummary).join("")
        : `<article class="reasoning-evidence-card"><h3>No factual evidence packets</h3><p>Evidence packets appear after source observations are compressed into dashboard-safe records.</p></article>`;
    const missingHtml = asArray(model.missing_corroboration).length
        ? asArray(model.missing_corroboration).map(renderMissingCorroborationCard).join("")
        : `<article class="reasoning-missing-card online"><h3>No missing corroboration exported</h3><p>No missing corroboration blocker is visible in this snapshot.</p></article>`;
    const reviewHtml = asArray(model.review_chain).map(renderReasoningReviewCard).join("");
    const groups = new Map(asArray(model.reasoning_review_groups).map((group) => [group.id, group]));
    const priorEvidenceGroup = groups.get("prior_evidence_basis") || { id: "prior_evidence_basis", label: "Prior and evidence basis", summary: "", record_count: 0 };
    const hypothesesGroup = groups.get("hypotheses_blockers") || { id: "hypotheses_blockers", label: "Hypotheses and blockers", summary: "", record_count: 0 };
    const reviewGroup = groups.get("review_chain") || { id: "review_chain", label: "Review chain and quant annotation", summary: "", record_count: 0 };
    return `
        <section class="reasoning-workspace" data-reasoning-workspace>
            <div class="reasoning-workspace-head">
                <div>
                    <p class="label">Reasoning workspace</p>
                    <h2>${htmlText(model.question, "Why does Qadam care, and what is still missing?")}</h2>
                    <p>${htmlText(model.summary, "Reasoning queue has not loaded.")}</p>
                </div>
                <div class="reasoning-boundary-card">
                    ${renderInlineBadge("Research-only", "blocked")}
                    ${renderInlineBadge("Prior, not evidence", "blocked")}
                    ${renderInlineBadge("Hypothesis, not trade idea", "blocked")}
                    ${renderInlineBadge("No paper/order authority", "online")}
                    <p>${htmlText(model.boundary, "Reasoning is read-only and cannot create trade state.")}</p>
                </div>
            </div>
            <section class="reasoning-consolidated-readout ${statusClass(model.tone)}" data-reasoning-consolidated-readout>
                <div>
                    <p class="label">Reasoning readout</p>
                    <h3>Can this idea move beyond research?</h3>
                    <p>${htmlText(model.summary, "Reasoning queue has not loaded.")} Priors, evidence, hypotheses, and reviews remain separated below.</p>
                </div>
                <div class="reasoning-consolidated-metrics">
                    ${renderMetric("Hypotheses", model.counts?.hypotheses || 0)}
                    ${renderMetric("Research goals", model.counts?.research_goals || 0)}
                    ${renderMetric("Evidence packets", model.counts?.evidence_packets || 0)}
                    ${renderMetric("Evidence items", model.counts?.evidence_items || 0)}
                    ${renderMetric("Research packets", model.counts?.shadow_packets || 0)}
                    ${renderMetric("Strategy packets", model.counts?.strategy_packets || 0)}
                    ${renderMetric("Executable", model.counts?.executable_hypotheses || 0)}
                </div>
                <div class="tag-row">
                    ${renderInlineBadge("Prior is not evidence", "blocked")}
                    ${renderInlineBadge("Hypothesis is not trade idea", "blocked")}
                    ${renderInlineBadge("Model output cannot create orders", "online")}
                    ${renderInlineBadge("Review chain is challenge-only", "pending")}
                </div>
            </section>
            <div class="reasoning-lane-grid">${lanesHtml}</div>
            <div class="reasoning-review-groups" data-reasoning-review-groups>
                ${renderReasoningReviewGroup(priorEvidenceGroup, `
                    ${renderWorldviewPriorSummary(model.worldview_prior || {})}
                    <section class="reasoning-section">
                        <div class="reasoning-section-head">
                            <div>
                                <p class="label">Factual evidence</p>
                                <h3>Evidence packets and source trail</h3>
                            </div>
                            ${renderInlineBadge("Evidence, not order", "online")}
                        </div>
                        <div class="reasoning-evidence-grid">${evidenceHtml}</div>
                    </section>
                `, true)}
                ${renderReasoningReviewGroup(hypothesesGroup, `
                    <section class="reasoning-section">
                        <div class="reasoning-section-head">
                            <div>
                                <p class="label">Research goal queue</p>
                                <h3>What Qadam is watching before hypotheses</h3>
                            </div>
                            ${renderInlineBadge("Pre-signal research", "pending")}
                        </div>
                        <div class="reasoning-hypothesis-stack">${researchGoalHtml}</div>
                    </section>
                    <section class="reasoning-section">
                        <div class="reasoning-section-head">
                            <div>
                                <p class="label">Hypothesis queue</p>
                                <h3>Why ideas advanced, stalled, or were blocked</h3>
                            </div>
                            ${renderInlineBadge("Hypothesis, not trade idea", "blocked")}
                        </div>
                        <div class="reasoning-hypothesis-stack">${hypothesesHtml}</div>
                    </section>
                    <section class="reasoning-section">
                        <div class="reasoning-section-head">
                            <div>
                                <p class="label">Missing corroboration</p>
                                <h3>Normal blockers before trade state</h3>
                            </div>
                            ${renderInlineBadge("Hold until resolved", "blocked")}
                        </div>
                        <div class="reasoning-missing-grid">${missingHtml}</div>
                    </section>
                `)}
                ${renderReasoningReviewGroup(reviewGroup, `
                    <section class="reasoning-section">
                        <div class="reasoning-section-head">
                            <div>
                                <p class="label">Review chain</p>
                                <h3>Research Analyst, Strategy Lead, Signal Integrity, and Head of Quant</h3>
                            </div>
                            ${renderInlineBadge("Challenge-only", "pending")}
                        </div>
                        <div class="reasoning-review-grid">${reviewHtml}</div>
                        ${renderQuantAnnotationCard(model.quant_annotation || {})}
                    </section>
                `)}
            </div>
        </section>
    `;
}

function renderCognition(status, viewModels = {}) {
    const target = dashboardQuery("[data-cognition]");
    if (!target) return;

    const cognition = status.cognition || {};
    const reasoning = viewModels?.reasoning_model || buildReasoningModel(status);
    const hypotheses = asArray(cognition.hypotheses);
    const evidencePackets = asArray(cognition.evidence_packets);
    const shadowPackets = asArray(cognition.shadow_packets);
    const localResearch = asArray(cognition.local_research_assessments);
    const strategyPackets = asArray(cognition.strategy_lead_packets);
    const activity = asArray(cognition.model_activity);
    const focus = asArray(cognition.current_focus);
    const timeline = asArray(cognition.analysis_timeline);
    const blockedReasons = asArray(cognition.blocked_reasons);
    const accountContext = cognition.paper_account_context || {};
    const signalIntegrity = cognition.signal_integrity || {};
    const signalReviews = asArray(cognition.signal_integrity_reviews);
    const philosophy = status.decision_philosophy || {};
    const evidenceBySignal = evidencePackets.reduce((acc, packet) => {
        if (packet.signal_id) acc[packet.signal_id] = packet;
        return acc;
    }, {});
    const evidenceItemCount = sumNestedItems(evidencePackets, "items");
    const executableHypotheses = hypotheses.filter((hypothesis) => hypothesis.execution_allowed);
    const latestAssessment = localResearch[localResearch.length - 1] || {};
    const accountPositions = asArray(accountContext.position_summaries);
    const accountOrders = asArray(accountContext.order_summaries);
    const timelineHtml = timeline.length
        ? timeline.map((step) => `<li>${htmlText(step)}</li>`).join("")
        : `<li>${htmlText("trade layer not reached")}</li>`;

    const hypothesisHtml = hypotheses.length
        ? hypotheses.slice(0, 5).map((hypothesis) => {
            const packet = evidenceBySignal[hypothesis.signal_id] || {};
            const evidenceItems = asArray(packet.items);
            const evidenceHtml = evidenceItems.length
                ? evidenceItems.slice(0, 3).map((item) => `
                    <li>
                        <strong>${htmlText(item.source, "evidence source")}</strong>
                        <span>${htmlText(item.summary, "No summary")} · trust ${htmlText(item.trust_score, "n/a")}</span>
                    </li>
                `).join("")
                : `<li><strong>No evidence packet</strong><span>Waiting for corroborated source observations.</span></li>`;
            return `
                <article class="cognition-card hypothesis-card">
                    <div class="cognition-card-head">
                        ${renderStatusPill(hypothesis.status || "blocked")}
                        <p class="label">${htmlText(hypothesis.instrument_focus, "instrument watchlist")}</p>
                    </div>
                    <h3>${htmlText(hypothesis.title, "Shadow hypothesis")}</h3>
                    <p>${htmlText(hypothesis.thesis, "No thesis yet.")}</p>
                    <div class="tag-row">
                        ${renderInlineBadge("Hypothesis, not trade", "blocked")}
                        ${renderInlineBadge("Execution blocked", "blocked")}
                        ${renderInlineBadge(`created ${formatTime(hypothesis.created_at)}`, "pending")}
                        ${renderInlineBadge(`packet ${dashboardText(hypothesis.evidence_packet_id, "not linked")}`, packet.signal_id ? "online" : "pending")}
                    </div>
                    <div class="summary-strip compact">
                        ${renderMetric("Confidence", formatConfidence(hypothesis.confidence))}
                        ${renderMetric("Evidence", htmlText(hypothesis.evidence_source_count, "0"))}
                        ${renderMetric("Integrity", htmlText(hypothesis.integrity_review_status, "not reviewed"))}
                        ${renderMetric("Score", dashboardText(hypothesis.integrity_score, "n/a"))}
                        ${renderMetric("Execution", hypothesis.execution_allowed ? "Allowed" : "Blocked")}
                        ${renderMetric("Generated by", htmlText(hypothesis.generated_by, "unknown"))}
                    </div>
                    <dl class="cognition-facts">
                        <div>
                            <dt>Blocked because</dt>
                            <dd>${htmlText(hypothesis.blocked_reason, "blocked")}</dd>
                        </div>
                        <div>
                            <dt>Invalidation</dt>
                            <dd>${htmlText(hypothesis.invalidation, "No invalidation recorded.")}</dd>
                        </div>
                        <div>
                            <dt>Missing corroboration</dt>
                            <dd class="tag-row">${renderTagList(hypothesis.missing_correlations, "No missing correlations recorded")}</dd>
                        </div>
                        <div>
                            <dt>Boundary</dt>
                            <dd>Hypothesis only. It cannot enter the trade layer until the Signal Integrity Gate and Risk Agent exist.</dd>
                        </div>
                    </dl>
                    ${renderDecisionWorldviewBlock(philosophy)}
                    <ul class="evidence-list">${evidenceHtml}</ul>
                </article>
            `;
        }).join("")
        : `
            <article class="cognition-card hypothesis-card">
                <h3>No hypotheses yet</h3>
                <p>Qadam is waiting for shadow intelligence inputs before showing a live analysis queue.</p>
            </article>
        `;

    const activityHtml = activity.length
        ? activity.map((model) => `
            <article class="model-activity-card">
                <p class="label">${htmlText(model.role, "model role")}</p>
                <h3>${htmlText(model.status, "not called")}</h3>
                <p>${htmlText(model.current_task, "No current task.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(model.provider, model.status)}
                    ${renderInlineBadge(model.model, model.status)}
                    ${renderInlineBadge(model.authority, "blocked")}
                </div>
            </article>
        `).join("")
        : `<article class="model-activity-card"><h3>No model activity yet</h3><p>Provider checks have not run.</p></article>`;

    const shadowPacketHtml = shadowPackets.length
        ? shadowPackets.slice(0, 5).map((packet) => `
            <li>
                <strong>${htmlText(packet.agent_key, "research analyst")} · ${htmlText(packet.status, "queued")}</strong>
                <span>${htmlText(packet.summary, "No packet summary")} · ${htmlText(packet.uncertainty, "uncertainty unknown")} uncertainty</span>
                <small>${htmlText(asArray(packet.source_event_refs).join(", "), "No source refs")} · ${formatTime(packet.created_at)}</small>
                <small>${htmlText(packet.boundary, "Shadow triage only. No execution authority.")}</small>
            </li>
        `).join("")
        : `<li><strong>No shadow packets</strong><span>Research queue is empty.</span></li>`;

    const evidencePacketHtml = evidencePackets.length
        ? evidencePackets.slice(0, 5).map((packet) => {
            const packetItems = asArray(packet.items);
            const itemHtml = packetItems.length
                ? packetItems.slice(0, 3).map((item) => `
                    <li>
                        <strong>${htmlText(item.source, "evidence source")}</strong>
                        <span>${htmlText(item.event_type, "event")} · ${htmlText(item.summary, "No summary")}</span>
                    </li>
                `).join("")
                : `<li><strong>No evidence items</strong><span>Waiting for source observations.</span></li>`;
            return `
                <article class="evidence-packet-card">
                    <h3>${htmlText(packet.trail_id, "Evidence packet")}</h3>
                    <div class="tag-row">
                        ${renderInlineBadge(`${packet.source_count || 0} sources`, packet.source_count ? "online" : "pending")}
                        ${renderInlineBadge(`${packetItems.length} evidence items`, packetItems.length ? "online" : "pending")}
                        ${renderInlineBadge(`avg trust ${dashboardText(packet.average_trust_score, "n/a")}`, packet.average_trust_score ? "online" : "pending")}
                        ${renderInlineBadge(`min trust ${dashboardText(packet.min_trust_score, "n/a")}`, packet.min_trust_score ? "online" : "pending")}
                        ${renderInlineBadge(`created ${formatTime(packet.created_at)}`, "pending")}
                    </div>
                    <dl class="cognition-facts">
                        <div>
                            <dt>Sources</dt>
                            <dd>${htmlText(asArray(packet.sources).join(", "), "No sources recorded")}</dd>
                        </div>
                        <div>
                            <dt>Missing</dt>
                            <dd>${htmlText(asArray(packet.missing_correlations).join(", "), "none recorded")}</dd>
                        </div>
                    </dl>
                    <ul class="evidence-list">${itemHtml}</ul>
                </article>
            `;
        }).join("")
        : `<article class="evidence-packet-card"><h3>No evidence packets</h3><p class="mini">Evidence packets appear after shadow triage has source observations.</p></article>`;

    const localResearchHtml = localResearch.length
        ? localResearch.slice(-3).reverse().map((assessment) => `
            <article class="cognition-card research-assessment-card">
                <div class="cognition-card-head">
                    ${renderStatusPill(assessment.status || "shadow_only")}
                    <p class="label">${htmlText(assessment.mode, "local assessment")}</p>
                </div>
                <h3>${htmlText(assessment.watch_focus, "Research Analyst focus")}</h3>
                <p>${htmlText(assessment.summary, "No local assessment summary.")}</p>
                <div class="summary-strip compact">
                    ${renderMetric("Confidence", formatConfidence(assessment.confidence))}
                    ${renderMetric("Escalation", htmlText(assessment.escalation_recommendation, "hold shadow"))}
                    ${renderMetric("Execution", assessment.execution_allowed ? "Allowed" : "Blocked")}
                    ${renderMetric("Paper order", assessment.paper_order_allowed ? "Allowed" : "Blocked")}
                </div>
                <section class="trade-check-section">
                    <p class="label">Anomalies</p>
                    <div class="tag-row">${renderTagList(assessment.anomalies, "No anomalies recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Missing corroboration</p>
                    <div class="tag-row">${renderTagList(assessment.missing_correlations, "No missing correlations recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Next questions</p>
                    <div class="tag-row">${renderTagList(assessment.next_questions, "No questions recorded")}</div>
                </section>
                <p class="mini">${htmlText(assessment.provider, "local")} · ${htmlText(assessment.model, "model")} · ${formatTime(assessment.created_at)}</p>
            </article>
        `).join("")
        : `<article class="cognition-card research-assessment-card"><h3>No local assessment yet</h3><p>The Research Analyst has not compressed the shadow queue.</p></article>`;

    const strategyLeadHtml = strategyPackets.length
        ? strategyPackets.slice(-3).reverse().map((packet) => {
            const sourceContext = packet.source_context || {};
            const review = packet.strategy_review || {};
            return `
                <article class="cognition-card strategy-lead-card">
                    <div class="cognition-card-head">
                        ${renderStatusPill(packet.status || "queued_shadow_only")}
                        <p class="label">${htmlText(review.review_mode, "strategy handoff")}</p>
                    </div>
                    <h3>${htmlText(packet.watch_focus, "Strategy Lead review")}</h3>
                    <p>${htmlText(review.boundary || packet.boundary, "Strategy Lead review is challenge-only and non-executable.")}</p>
                    <div class="summary-strip compact">
                        ${renderMetric("Source posture", htmlText(review.source_posture, "unknown"))}
                        ${renderMetric("Mode", htmlText(sourceContext.mode, "unknown"))}
                        ${renderMetric("Replay", `${sourceContext.durable_replay_replayed_source_count || 0}/${sourceContext.source_count || 0}`)}
                        ${renderMetric("Queued", sourceContext.queued_packet_count || 0)}
                        ${renderMetric("Pressure", htmlText(review.evidence_pressure, "thin"))}
                        ${renderMetric("Trade candidate", review.trade_candidate_allowed ? "Allowed" : "Blocked")}
                    </div>
                    <section class="trade-check-section">
                        <p class="label">Required challenges</p>
                        <div class="tag-row">${renderTagList(review.required_challenges, "No strategy challenges recorded")}</div>
                    </section>
                    <section class="trade-check-section">
                        <p class="label">Blocked by</p>
                        <div class="tag-row">${renderTagList(packet.blocked_by, "No blocks recorded")}</div>
                    </section>
                    <p class="mini">${htmlText(packet.worldview_lens_status, "private prior only")} · ${formatTime(packet.created_at)}</p>
                </article>
            `;
        }).join("")
        : `<article class="cognition-card strategy-lead-card"><h3>No Strategy Lead handoff yet</h3><p>The Strategy Lead has not received a shadow packet.</p></article>`;

    const paperContextHtml = `
        <article class="cognition-card paper-context-card">
            <div class="cognition-card-head">
                ${renderStatusPill(accountContext.status || "pending")}
                <p class="label">${htmlText(accountContext.connection_status, "paper mirror")}</p>
            </div>
            <h3>Paper account context</h3>
            <p>${htmlText(accountContext.capital_policy, "The first-release paper account has GBP 100,000 available. GBP 1,000 is only a single-order/notional risk cap when shown.")}</p>
            <div class="summary-strip compact">
                ${renderMetric("Trial policy", formatMoney(accountContext.trial_allocation_gbp))}
                ${renderMetric("Broker mirror", formatMoney(accountContext.current_balance_gbp))}
                ${renderMetric("Open positions", accountContext.open_position_count || 0)}
                ${renderMetric("Orders", accountContext.order_count || 0)}
                ${renderMetric("Drawdown", formatPercent(accountContext.drawdown_pct))}
                ${renderMetric("Execution", accountContext.execution_allowed ? "Allowed" : "Blocked")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(accountContext.write_authority ? "write enabled" : "read only", accountContext.write_authority ? "blocked" : "online")}
                ${renderInlineBadge(accountContext.paper_order_allowed ? "paper order allowed" : "no paper order authority", accountContext.paper_order_allowed ? "blocked" : "online")}
                ${renderInlineBadge(accountContext.live_capital_enabled ? "live capital" : "live capital disabled", accountContext.live_capital_enabled ? "blocked" : "online")}
                ${renderInlineBadge(`${accountContext.maturity_closed_trade_count || 0}/${accountContext.maturity_closed_trade_target || 100} paper trades`, "pending")}
            </div>
            <dl class="cognition-facts">
                <div>
                    <dt>Exposure</dt>
                    <dd>${accountPositions.length ? accountPositions.map((position) => `${htmlText(position.instrument, "instrument")} ${htmlText(position.direction, "direction")} ${htmlText(position.quantity, "0")}`).join(", ") : "No open exposure mirrored."}</dd>
                </div>
                <div>
                    <dt>Orders</dt>
                    <dd>${accountOrders.length ? accountOrders.map((order) => `${htmlText(order.instrument, "instrument")} ${htmlText(order.direction, "direction")} ${htmlText(order.status, "status")}`).join(", ") : "No mirrored paper orders."}</dd>
                </div>
                <div>
                    <dt>Boundary</dt>
                    <dd>${htmlText(accountContext.boundary, "Read-only paper account context. No order authority.")}</dd>
                </div>
            </dl>
        </article>
    `;

    const signalIntegrityHtml = signalReviews.length
        ? signalReviews.slice(-5).reverse().map((review) => {
            const marketPolicy = review.market_confirmation_policy || {};
            return `
            <article class="cognition-card signal-integrity-card">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "hold_for_corroboration")}
                    <p class="label">${htmlText(review.instrument_focus, "signal focus")}</p>
                </div>
                <h3>Signal Integrity Review</h3>
                <p>${htmlText(review.boundary, "Signal Integrity Gate is non-executable.")}</p>
                <div class="summary-strip compact">
                    ${renderMetric("Score", dashboardText(review.integrity_score, "n/a"))}
                    ${renderMetric("Sources", review.source_count || 0)}
                    ${renderMetric("Evidence", review.evidence_item_count || 0)}
                    ${renderMetric("Avg trust", dashboardText(review.average_trust_score, "n/a"))}
                    ${renderMetric("Min trust", dashboardText(review.min_trust_score, "n/a"))}
                    ${renderMetric("Market", htmlText(marketPolicy.status, "not checked"))}
                    ${renderMetric("Trade created", review.trade_candidate_created ? "Yes" : "No")}
                </div>
                <section class="trade-check-section">
                    <p class="label">Market confirmation</p>
                    <div class="tag-row">
                        ${renderInlineBadge(marketPolicy.uses_yahoo_finance ? "Yahoo Finance supplemental" : "No Yahoo context", marketPolicy.uses_yahoo_finance ? "pending" : "blocked")}
                        ${renderInlineBadge(marketPolicy.status || "not checked", marketPolicy.status === "market_confirmation_corroboration_available" ? "online" : "blocked")}
                        ${renderInlineBadge(marketPolicy.pricing_gap || "pricing gap required", "blocked")}
                        ${renderInlineBadge(marketPolicy.signal_authority ? "signal authority" : "no signal authority", marketPolicy.signal_authority ? "blocked" : "online")}
                        ${renderInlineBadge(marketPolicy.order_authority ? "order authority" : "no order authority", marketPolicy.order_authority ? "blocked" : "online")}
                        ${renderInlineBadge(marketPolicy.broker_reconciliation_authority ? "reconciliation authority" : "no reconciliation truth", marketPolicy.broker_reconciliation_authority ? "blocked" : "online")}
                    </div>
                    <p class="mini">${htmlText(marketPolicy.boundary, "Market confirmation is supplemental only and cannot create orders.")}</p>
                </section>
                <section class="trade-check-section">
                    <p class="label">Akber filter</p>
                    <div class="tag-row">${renderTagList(Object.entries(review.akber_filter || {}).map(([key, value]) => `${key}: ${value}`), "No Akber stage output")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Failure reasons</p>
                    <div class="tag-row">${renderTagList(review.failure_reasons, "No failure reasons recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <div class="tag-row">${renderTagList(review.required_next_steps, "No next steps recorded")}</div>
                </section>
                <p class="mini">${htmlText(review.worldview_prior_status, "private prior only")} · ${formatTime(review.reviewed_at)}</p>
            </article>
        `;
        }).join("")
        : `<article class="cognition-card signal-integrity-card"><h3>No Signal Integrity reviews yet</h3><p>Shadow signals have not been audited by the Signal Auditor.</p></article>`;

    target.innerHTML = `
        ${renderReasoningWorkspace(reasoning)}
        <details class="reasoning-review-group reasoning-advanced-diagnostics" data-reasoning-review-group="advanced_diagnostics">
            <summary>
                <strong>Advanced cognition diagnostics</strong>
                <span>Legacy detail for paper context, model activity, local research, strategy handoff, and signal integrity.</span>
                <em>${htmlText(activity.length + shadowPackets.length + localResearch.length + strategyPackets.length + signalReviews.length)} records</em>
            </summary>
            <div class="reasoning-review-group-body">
                <section class="cognition-section">
                    <p class="label">Cognition state</p>
                    <div class="summary-strip compact">
                        ${renderMetric("State", cognition.status || "shadow ready")}
                        ${renderMetric("Focus items", focus.length)}
                        ${renderMetric("Hypotheses", hypotheses.length)}
                        ${renderMetric("Evidence items", evidenceItemCount)}
                        ${renderMetric("Shadow packets", shadowPackets.length)}
                        ${renderMetric("Local assessments", localResearch.length)}
                        ${renderMetric("Strategy packets", strategyPackets.length)}
                        ${renderMetric("Integrity reviews", signalReviews.length)}
                        ${renderMetric("Models", activity.length)}
                        ${renderMetric("Execution", executableHypotheses.length ? "Unexpected allowed" : "Blocked")}
                    </div>
                    <div class="tag-row">
                        ${renderInlineBadge("Hypothesis, not trade", "blocked")}
                        ${renderInlineBadge("Trade layer not reached", "blocked")}
                        ${renderInlineBadge(`Signal Integrity ${signalIntegrity.status || "pending"}`, signalIntegrity.status === "ok" ? "online" : "pending")}
                        ${renderInlineBadge(`latest local assessment ${formatTime(latestAssessment.created_at)}`, latestAssessment.created_at ? "online" : "pending")}
                    </div>
                </section>
                <section class="cognition-section">
                    <p class="label">Current focus</p>
                    <div class="focus-box">${renderTagList(focus, "No active focus")}</div>
                </section>
                <section class="cognition-section">
                    <p class="label">Paper account context</p>
                    <div class="hypothesis-stack">${paperContextHtml}</div>
                </section>
                <section class="cognition-section">
                    <p class="label">Signal Integrity Gate</p>
                    <div class="summary-strip compact">
                        ${renderMetric("Total reviews", signalIntegrity.review_count || 0)}
                        ${renderMetric("Held", (signalIntegrity.by_status || {}).hold_for_corroboration || 0)}
                        ${renderMetric("Blocked", (signalIntegrity.by_status || {}).blocked || 0)}
                        ${renderMetric("Risk shadow", (signalIntegrity.by_status || {}).passed_to_risk_shadow || 0)}
                        ${renderMetric("Candidates created", signalIntegrity.trade_candidate_created_count || 0)}
                        ${renderMetric("Execution", signalIntegrity.execution_allowed_count ? "Unexpected allowed" : "Blocked")}
                    </div>
                    <div class="hypothesis-stack">${signalIntegrityHtml}</div>
                </section>
                <section class="cognition-section">
                    <p class="label">Model activity</p>
                    <div class="model-activity-grid">${activityHtml}</div>
                </section>
                <section class="cognition-section">
                    <p class="label">Shadow packets</p>
                    <ul class="status-list packet-list">${shadowPacketHtml}</ul>
                </section>
                <section class="cognition-section">
                    <p class="label">Local Research Analyst</p>
                    <div class="hypothesis-stack">${localResearchHtml}</div>
                </section>
                <section class="cognition-section">
                    <p class="label">Strategy Lead shadow review</p>
                    <div class="hypothesis-stack">${strategyLeadHtml}</div>
                </section>
                <section class="cognition-section">
                    <p class="label">Hypotheses and evidence</p>
                    <div class="hypothesis-stack">${hypothesisHtml}</div>
                </section>
                <section class="cognition-section">
                    <p class="label">Evidence packet index</p>
                    <div class="evidence-packet-grid">${evidencePacketHtml}</div>
                </section>
                <section class="cognition-section cognition-two-col">
                    <div>
                        <p class="label">Analysis timeline</p>
                        <ol class="timeline-list">${timelineHtml}</ol>
                    </div>
                    <div>
                        <p class="label">Blocked reasons</p>
                        <div class="tag-row">${renderTagList(blockedReasons, "No blocks recorded")}</div>
                    </div>
                </section>
                <p class="mini">${htmlText(cognition.boundary, "Shadow-only cognition.")}</p>
            </div>
        </details>
    `;
}

function renderDecisionWorldviewBlock(philosophy) {
    const lenses = asArray(philosophy.active_lenses).slice(0, 3);
    const lensTags = lenses.map((lens) => `${lens.claim_type}: ${lens.corroboration_status}`);
    return `
        <section class="trade-check-section worldview-decision-context">
            <p class="label">Worldview lens</p>
            <div class="tag-row">${renderTagList(lensTags, "No worldview lens recorded")}</div>
            <p class="mini">${htmlText(philosophy.boundary, "World-model claims are private priors, not evidence or trade triggers.")}</p>
        </section>
    `;
}

function renderWorldview(status) {
    const target = dashboardQuery("[data-worldview]");
    if (!target) return;
    const philosophy = status.decision_philosophy || {};
    const lenses = asArray(philosophy.active_lenses);
    const lensCards = lenses.length
        ? lenses.slice(0, 5).map((lens) => `
            <article class="evidence-packet-card">
                <p class="label">${htmlText(lens.claim_type, "worldview lens")}</p>
                <h3>${htmlText(lens.key, "private prior")}</h3>
                <p>${htmlText(lens.claim, "No claim text.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(lens.corroboration_status, "pending")}
                    ${renderInlineBadge(`${asArray(lens.live_sources_to_check).length} live checks`, "pending")}
                    ${renderInlineBadge(`${asArray(lens.market_channels).length} channels`, "pending")}
                </div>
                <p class="mini">${htmlText(lens.mechanism, "No mechanism recorded.")}</p>
            </article>
        `).join("")
        : `<article class="evidence-packet-card"><h3>No worldview cards</h3><p class="mini">The world-model corpus has not been exported into the status contract.</p></article>`;
    target.innerHTML = `
        ${renderPanelBrief({
            id: "private_edge_layer",
            question: "Which private priors are shaping the questions?",
            state: `${philosophy.claim_count || 0} claim cards`,
            tone: philosophy.status === "ok" ? "online" : "pending",
            primary: `${philosophy.corpus_file_count || 0} corpus files and ${philosophy.foundational_prior_count || 0} foundational priors are available as context.`,
            secondary: "Priors being mistaken for evidence, market channels without live corroboration, or a missing observable to check. The full private-prior distinction now appears in the Reasoning workspace above.",
            boundary: philosophy.boundary || "Worldview is context only, not evidence, and cannot trigger trades."
        })}
        <section class="reasoning-merge-note">
            <p class="label">Merged into Reasoning workspace</p>
            <h3>Private Edge is now prior context inside Reasoning</h3>
            <p>These cards remain as a compact prior index, while the main Reasoning workspace separates worldview prior, factual evidence, hypotheses, missing corroboration, Strategy Lead review, and Head of Quant annotation.</p>
        </section>
        <div class="summary-strip">
            ${renderMetric("Corpus files", htmlText(philosophy.corpus_file_count, "0"))}
            ${renderMetric("Claim cards", htmlText(philosophy.claim_count, "0"))}
            ${renderMetric("Private priors", htmlText(philosophy.foundational_prior_count, "0"))}
            ${renderMetric("Authority", "Prior only")}
        </div>
        <p class="empty-state">${htmlText(philosophy.trading_philosophy, "Qadam's private worldview shapes questions, not direct execution.")}</p>
        <section class="cognition-section">
            <p class="label">Decision chain</p>
            <ol class="timeline-list">${asArray(philosophy.decision_chain).map((step) => `<li>${htmlText(step)}</li>`).join("")}</ol>
        </section>
        <section class="cognition-section">
            <p class="label">Active private lenses</p>
            <div class="evidence-packet-grid">${lensCards}</div>
        </section>
        <p class="mini">${htmlText(philosophy.boundary, "World-model claims are private priors, not factual evidence or trade triggers.")}</p>
    `;
}

function renderForbidden(status) {
    const target = dashboardQuery("[data-forbidden-actions]");
    if (!target) return;
    const actions = asArray(status.forbidden_actions);
    const brokerBlocked = actions.some((action) => /broker|write/i.test(`${action.key || ""} ${action.reason || ""}`));
    replacePanelBrief("forbidden_actions", {
        question: "Which paths have hard safety stops?",
        state: `${actions.length} safety stops`,
        tone: actions.length ? "blocked" : "pending",
        primary: actions.length
            ? `Qadam is carrying ${actions.length} explicit safety stops in this snapshot. Broker writes are ${brokerBlocked ? "stopped" : "not separately recorded"}.`
            : "No forbidden-action records have been exported into this snapshot.",
        secondary: "Live-capital, broker-write, stale-data, missing-credential, risk, and kill-switch boundaries.",
        boundary: "This panel reports hard stops only. It cannot unlock blocked authority or create an exception."
    });
    target.innerHTML = actions.length
        ? actions.map((action) => `
            <li>
                <strong>${htmlText(action.key)}</strong>
                <span>${htmlText(action.reason)}</span>
            </li>
        `).join("")
        : `
            <li>
                <strong>Not connected yet</strong>
                <span>No forbidden-action records have been exported into this snapshot.</span>
            </li>
        `;
}

function renderGovernanceTargetButton(target) {
    return `
        <button type="button" class="governance-target-button" data-comment-target-button data-target-type="${literalHtmlText(target.target_type)}" data-target-key="${literalHtmlText(target.target_key)}">
            <span>${htmlText(target.view)}</span>
            <strong>${htmlText(target.label)}</strong>
            <p>${htmlText(target.helper)}</p>
        </button>
    `;
}

function renderGovernanceRecord(record) {
    return `
        <article class="governance-record-card ${statusClass(record.tone)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(record.state)}
                ${renderInlineBadge(record.event_log_written ? "Event Log linked" : "audit-only", record.event_log_written ? "online" : "pending")}
            </div>
            <h3>${htmlText(record.label)}</h3>
            <p>${htmlText(record.detail)}</p>
            <small>${htmlText(record.boundary)}</small>
        </article>
    `;
}

function renderGovernanceAction(action) {
    return `
        <a class="governance-action ${statusClass(action.tone)}" href="${literalHtmlText(action.href)}">
            <strong>${htmlText(action.label)}</strong>
            <span>${htmlText(action.detail)}</span>
        </a>
    `;
}

function renderGovernanceMessage(message) {
    return `
        <li>
            <strong>${htmlText(message.title, "Telegram message")}</strong>
            <span>${htmlText(message.message_class, "message")} · ${htmlText(message.target_ref, "qadam")}</span>
            <div class="comment-meta">
                ${renderInlineBadge(message.status || "queued", message.status || "pending")}
                ${renderInlineBadge(message.mode || "dry_run", message.mode === "live_send" ? "blocked" : "pending")}
                ${renderInlineBadge(message.send_allowed ? "send allowed" : "send blocked", message.send_allowed ? "blocked" : "online")}
            </div>
            <small>${formatTime(message.created_at)}</small>
        </li>
    `;
}

function renderGovernanceWorkspace(model) {
    const comments = model.comments || {};
    const approvals = model.approvals || {};
    const reviewPacks = model.review_packs || {};
    const communications = model.communications || {};
    const livePromotion = model.live_promotion || {};
    const messages = asArray(communications.recent_messages);
    const messageRows = messages.length
        ? messages.slice(0, 5).map(renderGovernanceMessage).join("")
        : `<li><strong>No outbound messages</strong><span>No Telegram outbox messages are exported in this snapshot.</span></li>`;
    return `
        <section class="governance-workspace" data-governance-workspace-rendered>
            <div class="governance-workspace-head">
                <div>
                    <p class="label">Governance workspace</p>
                    <h3>Comments, approvals, reviews, and outbound communications</h3>
                    <p>${htmlText(model.summary)} Governance is where Fund Manager review happens, but it remains audit/comment state only.</p>
                </div>
                <article class="governance-boundary-card">
                    ${renderInlineBadge("comments governance-only", "online")}
                    ${renderInlineBadge("approvals audit-only", "pending")}
                    ${renderInlineBadge(communications.command_path_enabled ? "Telegram command path enabled" : "Telegram outbound-only", communications.command_path_enabled ? "blocked" : "online")}
                    ${renderInlineBadge(livePromotion.live_capital_enabled ? "live capital enabled" : "live capital disabled", livePromotion.live_capital_enabled ? "blocked" : "online")}
                    <p>${htmlText(model.boundary)}</p>
                </article>
            </div>

            <div class="governance-status-grid">
                ${renderMetric("Comments", comments.count || 0)}
                ${renderMetric("Suggestions", comments.suggestion_count || 0)}
                ${renderMetric("Accepted", comments.accepted_count || 0)}
                ${renderMetric("Implemented", comments.implemented_count || 0)}
                ${renderMetric("Approval", approvals.strategy_approval_state || "missing")}
                ${renderMetric("Weekly review", reviewPacks.weekly_review_pack_state || "not ready")}
                ${renderMetric("Telegram queue", communications.pending_queue_count || 0)}
                ${renderMetric("Live promotion", livePromotion.status || "not eligible")}
            </div>

            <section class="governance-comment-targets">
                <div class="overview-section-head">
                    <span>Comment shortcuts</span>
                    <strong>Comment without memorizing internal reference keys.</strong>
                </div>
                <div class="governance-target-grid">
                    ${asArray(model.comment_targets).map(renderGovernanceTargetButton).join("")}
                </div>
            </section>

            <section class="governance-review-grid">
                <div class="governance-review-section">
                    <div class="overview-section-head">
                        <span>Approval and certification records</span>
                        <strong>Audit state only unless a backend gate says otherwise.</strong>
                    </div>
                    <div class="governance-record-grid">
                        ${asArray(approvals.records).map(renderGovernanceRecord).join("")}
                    </div>
                </div>
                <div class="governance-review-section">
                    <div class="overview-section-head">
                        <span>Open action items</span>
                        <strong>What needs Fund Manager review next?</strong>
                    </div>
                    <div class="governance-action-list">
                        ${asArray(model.open_actions).map(renderGovernanceAction).join("")}
                    </div>
                </div>
            </section>

            <section class="governance-communications-card">
                <div class="overview-section-head">
                    <span>Telegram outbound state</span>
                    <strong>Visible communications, no command authority.</strong>
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Status", communications.telegram_status || "not exported")}
                    ${renderMetric("Dry-run", communications.dry_run_message_count || 0)}
                    ${renderMetric("Queued", communications.pending_queue_count || 0)}
                    ${renderMetric("Failed", communications.failed_count || 0)}
                    ${renderMetric("Suppressed", communications.suppressed_count || 0)}
                    ${renderMetric("Live sends", communications.live_send_allowed_count || 0)}
                    ${renderMetric("Commands", communications.command_path_enabled_count || 0)}
                    ${renderMetric("Send gate", communications.send_gate || "disabled")}
                </div>
                <div class="tag-row">
                    ${renderInlineBadge(communications.command_path_enabled ? "command path enabled" : "no Telegram command path", communications.command_path_enabled ? "blocked" : "online")}
                    ${renderInlineBadge(communications.live_send_allowed_count ? "live send allowed" : "live send disabled", communications.live_send_allowed_count ? "blocked" : "online")}
                    ${renderInlineBadge("outbound notify-only", "online")}
                </div>
                <ul class="status-list communications-list">${messageRows}</ul>
                <p class="mini">${htmlText(communications.boundary)}</p>
            </section>

            <section class="governance-weekly-card">
                <div class="overview-section-head">
                    <span>Weekly review and live-promotion workflow</span>
                    <strong>Review packs summarize proof state; they do not approve live capital.</strong>
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Review pack", reviewPacks.weekly_review_pack_state || "not ready")}
                    ${renderMetric("Proof week", `${reviewPacks.current_proof_week_number || 0}/${reviewPacks.proof_week_count || 5}`)}
                    ${renderMetric("Weekly target", `${reviewPacks.weekly_proof_trade_target || 3}/week`)}
                    ${renderMetric("Closed proof", reviewPacks.closed_proof_trade_count || 0)}
                    ${renderMetric("Postmortem due", reviewPacks.postmortem_due_count || 0)}
                    ${renderMetric("Promotion", livePromotion.status || "not eligible")}
                </div>
                <p>${htmlText(reviewPacks.boundary)} ${htmlText(livePromotion.boundary)}</p>
            </section>
        </section>
    `;
}

function syncGovernanceCommentTargetOptions(targets) {
    const select = dashboardQuery("[data-comment-target-select]");
    if (!select || typeof document.createElement !== "function") return;
    select.textContent = "";
    asArray(targets).forEach((target) => {
        const option = document.createElement("option");
        option.value = target.target_key;
        option.textContent = `${target.view} - ${target.label}`;
        option.dataset.targetType = target.target_type;
        select.appendChild(option);
    });
}

function initGovernanceCommentTargetButtons() {
    if (typeof document.querySelectorAll !== "function") return;
    const form = dashboardQuery("[data-comment-form]");
    if (!form) return;
    document.querySelectorAll("[data-comment-target-button]").forEach((button) => {
        if (button.dataset.targetButtonWired === "true") return;
        button.dataset.targetButtonWired = "true";
        button.addEventListener("click", () => {
            const type = button.dataset.targetType || "system";
            const key = button.dataset.targetKey || "general";
            const typeSelect = form.querySelector("[name='target_type']");
            const keySelect = form.querySelector("[name='target_key']");
            const body = form.querySelector("[name='body']");
            if (typeSelect) typeSelect.value = type;
            if (keySelect) keySelect.value = key;
            if (body && !body.value) {
                body.placeholder = `Governance note for ${button.textContent.trim().replace(/\s+/g, " ").slice(0, 80)}`;
            }
            form.scrollIntoView?.({ block: "center" });
        });
    });
    const targetSelect = form.querySelector("[data-comment-target-select]");
    if (targetSelect?.dataset.targetSelectWired === "true") return;
    if (targetSelect) targetSelect.dataset.targetSelectWired = "true";
    targetSelect?.addEventListener("change", () => {
        const selected = targetSelect.selectedOptions?.[0];
        const type = selected?.dataset?.targetType;
        const typeSelect = form.querySelector("[name='target_type']");
        if (type && typeSelect) typeSelect.value = type;
    });
}

function renderCommunications(status) {
    const target = dashboardQuery("[data-communications]");
    if (!target) return;
    const telegram = status.communications?.telegram || {};
    const telegramDailyDigest = status.communications?.telegram_daily_portfolio_digest || {};
    const telegramIntake = status.communications?.telegram_intake || {};
    const messages = asArray(telegram.recent_messages);
    const classes = asArray(telegram.active_message_classes);
    const intakeRecords = asArray(telegramIntake.recent_records);
    const dailyDigestTrades = asArray(telegramDailyDigest.daily_trade_summaries);
    const messageRows = messages.length
        ? messages.map((message) => `
            <li>
                <strong>${htmlText(message.title, "Telegram message")}</strong>
                <span>${htmlText(message.message_class, "message")} · ${htmlText(message.target_ref, "qadam")}</span>
                <div class="comment-meta">
                    ${renderInlineBadge(message.status || "queued", message.status || "pending")}
                    ${renderInlineBadge(message.mode || "dry_run", message.mode === "live_send" ? "degraded" : "pending")}
                    ${renderInlineBadge(message.send_allowed ? "send allowed" : "send blocked", message.send_allowed ? "degraded" : "online")}
                </div>
                <small>${formatTime(message.created_at)}</small>
            </li>
        `).join("")
        : `
            <li>
                <strong>No Telegram messages</strong>
                <span>No dry-run member communications have been queued yet.</span>
            </li>
        `;
    const intakeRows = intakeRecords.length
        ? intakeRecords.map((record) => `
            <li>
                <strong>${htmlText(record.intake_type, "member research")}</strong>
                <span>${htmlText(record.summary, "Telegram member-submitted research")}</span>
                <div class="comment-meta">
                    ${renderInlineBadge(record.status || "recorded", record.status || "online")}
                    ${renderInlineBadge(`${record.url_count || 0} source links`, record.url_count ? "online" : "pending")}
                    ${renderInlineBadge(record.research_triage_packet_created ? "Research packet" : "No research packet", record.research_triage_packet_created ? "online" : "pending")}
                    ${renderInlineBadge(record.strategy_consideration_written ? "Strategy consideration" : "World datapoint", record.strategy_consideration_written ? "online" : "pending")}
                </div>
                <small>${formatTime(record.observed_at)}</small>
            </li>
        `).join("")
        : `
            <li>
                <strong>No member research intake yet</strong>
                <span>Telegram messages that look like world events or strategy notes will appear here after ingestion.</span>
            </li>
        `;
    target.innerHTML = `
        ${renderPanelBrief({
            id: "telegram_communications",
            question: "What has Qadam told or learned from Telegram?",
            state: telegramIntake.status || telegram.status || "dry_run",
            tone: telegram.failed_count ? "degraded" : (telegramIntake.status === "ready" ? "online" : "pending"),
            primary: `${telegram.pending_queue_count || 0} queued outbound messages, ${telegramIntake.world_event_datapoint_count || 0} member world-event datapoints, and ${telegramIntake.strategy_consideration_count || 0} member strategy considerations are visible.`,
            secondary: "Outbound bot updates, daily portfolio digests, inbound member research, Research Analyst packet creation, Strategy Lead consideration intake, and command-authority boundaries.",
            boundary: telegramIntake.boundary || telegram.boundary || status.communications?.boundary || "Telegram is outbound notify-only and inbound read-only. It cannot place, approve, reject, modify, close, or resize trades."
        })}
        <div class="summary-strip compact">
            ${renderMetric("Status", telegram.status || "disabled")}
            ${renderMetric("Mode", telegram.mode || "dry_run")}
            ${renderMetric("Daily digest", telegramDailyDigest.status || telegram.daily_portfolio_digest_status || "not run")}
            ${renderMetric("Portfolio balance", formatMoney(telegramDailyDigest.portfolio_balance_gbp || telegram.daily_portfolio_digest_portfolio_balance_gbp))}
            ${renderMetric("P&L", `${formatMoney(telegramDailyDigest.portfolio_total_pnl_gbp || 0)} · ${formatPercent(telegramDailyDigest.portfolio_performance_pct || telegram.daily_portfolio_digest_portfolio_performance_pct || 0)}`)}
            ${renderMetric("Trades today", telegramDailyDigest.daily_trade_count || telegram.daily_portfolio_digest_daily_trade_count || 0)}
            ${renderMetric("Verified", telegram.verified_member_count || 0)}
            ${renderMetric("Pending", telegram.pending_member_count || 0)}
            ${renderMetric("Queued", telegram.pending_queue_count || 0)}
            ${renderMetric("Inbound records", telegramIntake.record_count || 0)}
            ${renderMetric("World datapoints", telegramIntake.world_event_datapoint_count || 0)}
            ${renderMetric("Strategy notes", telegramIntake.strategy_consideration_count || 0)}
            ${renderMetric("Research packets", telegramIntake.research_triage_packet_count || 0)}
            ${renderMetric("Failed", telegram.failed_count || 0)}
            ${renderMetric("Suppressed", telegram.suppressed_count || 0)}
            ${renderMetric("Last sent", formatTime(telegram.last_sent_time))}
        </div>
        <div class="tag-row">
            ${renderInlineBadge(`send gate ${telegram.send_gate || "disabled"}`, telegram.send_gate === "enabled" ? "degraded" : "online")}
            ${renderInlineBadge(telegram.bot_configured ? "bot configured" : "bot token missing", telegram.bot_configured ? "online" : "pending")}
            ${renderInlineBadge(telegram.default_chat_configured ? "chat configured" : "chat pending", telegram.default_chat_configured ? "online" : "pending")}
            ${renderInlineBadge(`${telegram.dry_run_message_count || 0} dry-run messages`, telegram.dry_run_message_count ? "online" : "pending")}
            ${renderInlineBadge(telegramDailyDigest.enabled ? "daily portfolio digest enabled" : "daily portfolio digest disabled", telegramDailyDigest.enabled ? "online" : "pending")}
            ${renderInlineBadge(telegramDailyDigest.dry_run ? "daily digest dry-run" : "daily digest live-send gate", telegramDailyDigest.dry_run ? "pending" : "online")}
            ${renderInlineBadge(telegramIntake.enabled ? "inbound intake enabled" : "inbound intake disabled", telegramIntake.enabled ? "online" : "pending")}
            ${renderInlineBadge(telegramIntake.telegram_command_authority ? "command authority" : "no Telegram command authority", telegramIntake.telegram_command_authority ? "blocked" : "online")}
        </div>
        <section class="trade-intent-section">
            <p class="label">Message classes</p>
            <div class="tag-row">${renderTagList(classes, "No message classes queued")}</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Daily portfolio digest</p>
            <div class="summary-strip compact">
                ${renderMetric("Local date", telegramDailyDigest.local_date || "not run")}
                ${renderMetric("Send after", `${telegramDailyDigest.delivery_after_local_time || "17:00"} ${telegramDailyDigest.timezone || ""}`)}
                ${renderMetric("Due", telegramDailyDigest.due_for_delivery ? "yes" : "not yet")}
                ${renderMetric("Sent today", telegramDailyDigest.live_send_succeeded || telegramDailyDigest.already_sent ? "yes" : "not yet")}
            </div>
            <ul class="status-list communications-list">
                <li>
                    <strong>Portfolio balance ${htmlText(formatMoney(telegramDailyDigest.portfolio_balance_gbp))}</strong>
                    <span>${htmlText(formatMoney(telegramDailyDigest.portfolio_total_pnl_gbp || 0))} total P&amp;L · ${htmlText(formatPercent(telegramDailyDigest.portfolio_performance_pct || 0))} since paper allocation.</span>
                    <div class="comment-meta">
                        ${renderInlineBadge(telegramDailyDigest.status || "not_run", telegramDailyDigest.live_send_succeeded ? "online" : "pending")}
                        ${renderInlineBadge(telegramDailyDigest.target === "group" ? "group chat" : "target pending", telegramDailyDigest.target === "group" ? "online" : "pending")}
                        ${renderInlineBadge(telegramDailyDigest.telegram_command_path_enabled ? "command authority" : "notify only", telegramDailyDigest.telegram_command_path_enabled ? "blocked" : "online")}
                    </div>
                </li>
                <li>
                    <strong>Trades today</strong>
                    <span>${dailyDigestTrades.length ? dailyDigestTrades.map((item) => htmlText(item)).join("; ") : "No paper trades recorded for this local day."}</span>
                </li>
            </ul>
            <p class="mini">${htmlText(telegramDailyDigest.boundary || "Daily Telegram portfolio digests are outbound status reports only.")}</p>
        </section>
        <section class="trade-intent-section">
            <p class="label">Inbound member research</p>
            <div class="summary-strip compact">
                ${renderMetric("Polling", telegramIntake.polling_mode || "not exported")}
                ${renderMetric("Ignored", telegramIntake.ignored_message_count || 0)}
                ${renderMetric("Latest type", telegramIntake.latest_intake_type || "none")}
                ${renderMetric("Latest", formatTime(telegramIntake.latest_observed_at))}
            </div>
            <ul class="status-list communications-list">${intakeRows}</ul>
        </section>
        <section class="trade-intent-section">
            <p class="label">Recent outbox</p>
            <ul class="status-list communications-list">${messageRows}</ul>
        </section>
        <p class="mini">${htmlText(telegram.boundary || status.communications?.boundary || "Telegram is outbound-only and notify-only.")} ${htmlText(telegramIntake.boundary || "Telegram inbound intake is read-only member research intake.")}</p>
    `;
}

function tradeStateLabel(status) {
    const labels = {
        observed_signal: "Watching",
        hypothesis: "Thinking About",
        candidate: "Considering Trade",
        blocked: "Blocked",
        risk_review: "Risk Review",
        staged_paper_order: "Preparing Paper Trade",
        submitted_paper_order: "Submitted Paper Trade",
        open_position: "Open Paper Position",
        exit_planned: "Exit Planned",
        closed_trade: "Closed",
        postmortem_due: "Postmortem Due",
        postmortem_complete: "Postmortem Complete"
    };
    return labels[status] || dashboardText(status, "Trade state unknown");
}

function renderTrades(status, viewModels = {}) {
    const target = dashboardQuery("[data-trade-layer]");
    if (!target) return;
    const tradeLayer = status.trade_layer || {};
    const tradingView = status.tradingview_alerts || {};
    const tradingViewMcp = status.tradingview_mcp || {};
    const riskAgent = tradeLayer.risk_agent || status.risk_agent || {};
    const riskReviews = asArray(riskAgent.reviews);
    const executionPolicy = tradeLayer.execution_policy || status.execution_policy || {};
    const executionPolicyReviews = asArray(executionPolicy.reviews);
    const stagedPaperOrder = tradeLayer.staged_paper_order || status.staged_paper_order || {};
    const stagedPaperOrderReviews = asArray(stagedPaperOrder.reviews);
    const brokerReconciliation = tradeLayer.broker_reconciliation || status.broker_reconciliation || {};
    const brokerReconciliationReviews = asArray(brokerReconciliation.reviews);
    const paperSubmitReceipt = tradeLayer.paper_submit_receipt || status.paper_submit_receipt || {};
    const paperSubmitReceiptReviews = asArray(paperSubmitReceipt.reviews);
    const signalReview = status.phase5_signal_review || {};
    const signalReviewRecords = asArray(signalReview.records);
    const paperTradeDrill = status.phase5_paper_trade_drill || {};
    const paperTradeDrillRecords = asArray(paperTradeDrill.records);
    const phase5Certification = status.phase5_certification || {};
    const phase5CertificationGates = asArray(phase5Certification.gate_records);
    const phase5Phase6Handoff = status.phase5_phase6_handoff || {};
    const phase6LearningLoop = status.phase6_learning_loop || {};
    const phase6Certification = status.phase6_certification || {};
    const phase7DemoProof = status.phase7_demo_proof || {};
    const summary = tradeLayer.summary || {};
    const philosophy = status.decision_philosophy || {};
    const worldviewBlock = renderDecisionWorldviewBlock(philosophy);
    const tradesModel = viewModels?.trades_model || buildTradesModel(status, viewModels);
    const rows = [
        ["Observed signals", asArray(tradeLayer.watching)],
        ["Candidates", asArray(tradeLayer.candidates)],
        ["Blocked", asArray(tradeLayer.blocked)],
        ["Staged orders", asArray(tradeLayer.staged_orders)],
        ["Submitted", asArray(tradeLayer.submitted_orders)],
        ["Open", asArray(tradeLayer.open_positions)],
        ["Closed", asArray(tradeLayer.closed_trades)],
        ["Postmortems due", asArray(tradeLayer.postmortems_due)]
    ];

    const renderObservedSignalCard = (signal) => {
        const indicatorState = signal.indicator_state || {};
        const indicatorTags = Object.entries(indicatorState).map(([key, value]) => `${key}: ${value}`);
        return `
            <article class="trade-intent-card pending">
                <div class="cognition-card-head">
                    ${renderStatusPill(signal.status || "observed_signal")}
                    <p class="label">${htmlText(tradeStateLabel(signal.status || "observed_signal"))} · ${htmlText(signal.source_type, "observed source")}</p>
                </div>
                <h3>${htmlText(signal.instrument || signal.symbol, "Observed signal")}</h3>
                <p>${htmlText(signal.trigger || signal.chart_context, "No alert trigger recorded.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge("Observed signal only", "pending")}
                    ${renderInlineBadge(signal.trade_candidate_created ? "candidate created" : "not a candidate", signal.trade_candidate_created ? "blocked" : "online")}
                    ${renderInlineBadge(signal.execution_allowed ? "execution allowed" : "execution blocked", signal.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(signal.paper_order_allowed ? "paper order allowed" : "no paper order", signal.paper_order_allowed ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Timeframe", htmlText(signal.timeframe, "unknown"))}
                    ${renderMetric("Setup", htmlText(signal.setup_type, "unknown"))}
                    ${renderMetric("Direction", htmlText(signal.direction, "watch"))}
                    ${renderMetric("Price", htmlText(signal.price, "not supplied"))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Indicator state</p>
                    <div class="tag-row">${renderTagList(indicatorTags, "No indicator state recorded")}</div>
                </section>
                ${worldviewBlock}
                <dl class="trade-facts">
                    <div>
                        <dt>Chart context</dt>
                        <dd>${htmlText(signal.chart_context, "No chart context.")}</dd>
                    </div>
                    <div>
                        <dt>Observed</dt>
                        <dd>${formatTime(signal.observed_at)} · received ${formatTime(signal.received_at)}</dd>
                    </div>
                    <div>
                        <dt>Authority</dt>
                        <dd>${signal.execution_allowed ? "Execution allowed" : "Execution blocked"} · ${signal.paper_order_allowed ? "paper order allowed" : "no paper order"}</dd>
                    </div>
                    <div>
                        <dt>Source</dt>
                        <dd>${htmlText(signal.source, "unknown")} · ${htmlText(signal.alert_id, "no alert id")}</dd>
                    </div>
                </dl>
                <p class="mini">${htmlText(signal.boundary, "Observed signal only.")}</p>
            </article>
        `;
    };

    const renderTradeIntentCard = (intent, tone = "pending") => {
        const filterEntries = Object.entries(intent.akber_filter || {});
        const riskEntries = Object.entries(intent.risk_checks || {});
        const filterHtml = filterEntries.length
            ? filterEntries.map(([key, value]) => {
                const normalized = String(value);
                return renderInlineBadge(`${key}: ${normalized}`, normalized.includes("failed") || normalized.includes("missing") ? "blocked" : "pending");
            }).join("")
            : renderInlineBadge("filter not recorded", "pending");
        const riskHtml = riskEntries.length
            ? riskEntries.map(([key, value]) => {
                const normalized = String(value);
                return renderInlineBadge(`${key}: ${normalized}`, normalized.includes("blocked") ? "blocked" : "pending");
            }).join("")
            : renderInlineBadge("risk checks not recorded", "pending");
        return `
            <article class="trade-intent-card ${statusClass(tone)}">
                <div class="cognition-card-head">
                    ${renderStatusPill(intent.status || tone)}
                    <p class="label">${htmlText(tradeStateLabel(intent.status || tone))} · ${htmlText(intent.venue, "venue unknown")}</p>
                </div>
                <h3>${htmlText(intent.instrument, "Trade intent")}</h3>
                <p>${htmlText(intent.catalyst, "No catalyst recorded.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(intent.status === "blocked" ? "Blocked trade" : "Candidate, not order", intent.status === "blocked" ? "blocked" : "pending")}
                    ${renderInlineBadge(intent.execution_allowed ? "execution allowed" : "execution blocked", intent.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(intent.paper_order_allowed ? "paper order allowed" : "no paper order", intent.paper_order_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(intent.source_type, "pending")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Direction", htmlText(intent.direction, "unknown"))}
                    ${renderMetric("Qadam prob.", formatProbability(intent.probability_estimate))}
                    ${renderMetric("Market prob.", formatProbability(intent.market_implied_probability))}
                    ${renderMetric("Risk", `${formatMoney(intent.risk_size_gbp)} / ${htmlText(intent.risk_size_pct, "0")}%`)}
                </div>
                <dl class="trade-facts">
                    <div>
                        <dt>Evidence</dt>
                        <dd>${htmlText(intent.evidence_summary, "No evidence summary.")}</dd>
                    </div>
                    <div>
                        <dt>Entry</dt>
                        <dd>${htmlText(intent.proposed_entry, "No entry recorded.")}</dd>
                    </div>
                    <div>
                        <dt>Invalidation</dt>
                        <dd>${htmlText(intent.invalidation, "No invalidation recorded.")}</dd>
                    </div>
                    <div>
                        <dt>Hold window</dt>
                        <dd>${htmlText(intent.holding_window, "Unknown")}</dd>
                    </div>
                    <div>
                        <dt>Blocked reason</dt>
                        <dd>${htmlText(intent.blocked_reason || intent.risk_state, "Not reviewed by Risk Agent")}</dd>
                    </div>
                    <div>
                        <dt>Strategy</dt>
                        <dd>${htmlText(intent.strategy, "No strategy recorded.")}</dd>
                    </div>
                    <div>
                        <dt>Price gap</dt>
                        <dd>${htmlText(intent.price_gap, "No price gap recorded.")}</dd>
                    </div>
                    <div>
                        <dt>Source signal</dt>
                        <dd>${htmlText(intent.source_signal_id, "No source signal id")} · updated ${formatTime(intent.updated_at)}</dd>
                    </div>
                </dl>
                <section class="trade-check-section">
                    <p class="label">Akber filter</p>
                    <div class="tag-row">${filterHtml}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Risk checks</p>
                    <div class="tag-row">${riskHtml}</div>
                </section>
                ${worldviewBlock}
                <section class="trade-check-section">
                    <p class="label">Tags</p>
                    <div class="tag-row">${renderTagList(intent.tags, "No tags recorded")}</div>
                </section>
                <p class="mini">${htmlText(intent.boundary, "Trade intent only. No broker route exists.")}</p>
            </article>
            `;
    };

    const renderRiskReviewCard = (review) => {
        const checkTags = Object.entries(review.checks || {}).map(([key, value]) => `${key}: ${value}`);
        return `
            <article class="trade-intent-card ${statusClass(review.status || "policy_hold")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "policy_hold")}
                    <p class="label">${htmlText(review.source_type, "risk review")} · ${htmlText(review.source_ref, "source pending")}</p>
                </div>
                <h3>${htmlText(review.instrument, "Risk policy review")}</h3>
                <p>${htmlText(review.boundary, "Risk Agent review is read-only.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(review.execution_allowed ? "execution allowed" : "execution blocked", review.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.paper_order_allowed ? "paper order allowed" : "no paper order", review.paper_order_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.order_created ? "order created" : "no order created", review.order_created ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_write_allowed ? "broker write allowed" : "broker write blocked", review.broker_write_allowed ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Policy score", formatProbability(review.policy_score))}
                    ${renderMetric("Risk asked", `${formatMoney(review.proposed_risk_gbp)} / ${htmlText(review.proposed_risk_pct, "0")}%`)}
                    ${renderMetric("Max risk", `${formatMoney(review.max_risk_gbp)} / ${htmlText(review.max_risk_pct, "1")}%`)}
                    ${renderMetric("Signal", htmlText(review.signal_integrity_status, "not reviewed"))}
                    ${renderMetric("Account", htmlText(review.paper_account_status, "unknown"))}
                    ${renderMetric("Reviewed", formatTime(review.reviewed_at))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Risk checks</p>
                    <div class="tag-row">${renderTagList(checkTags, "No risk checks recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Blocked reasons</p>
                    <div class="tag-row">${renderTagList(review.blocked_reasons, "No blocking reason recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <ul class="status-list">${asArray(review.required_next_steps).length
                        ? asArray(review.required_next_steps).map((step) => `<li><strong>${htmlText(step)}</strong></li>`).join("")
                        : "<li><strong>No next steps recorded</strong></li>"
                    }</ul>
                </section>
            </article>
        `;
    };

    const renderExecutionPolicyCard = (review) => {
        const checkTags = Object.entries(review.checks || {}).map(([key, value]) => `${key}: ${value}`);
        const killSwitchTags = Object.entries(review.kill_switches || {}).map(([key, value]) => `${key}: ${value}`);
        return `
            <article class="trade-intent-card ${statusClass(review.status || "blocked_by_policy")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "blocked_by_policy")}
                    <p class="label">Execution Policy · ${htmlText(review.source_risk_review_id, "risk review pending")}</p>
                </div>
                <h3>${htmlText(review.instrument, "Execution policy review")}</h3>
                <p>${htmlText(review.boundary, "Execution policy is read-only.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(review.execution_allowed ? "execution allowed" : "execution blocked", review.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.staged_paper_order_allowed ? "staged order allowed" : "no staged paper order", review.staged_paper_order_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.paper_order_created ? "paper order created" : "no paper order created", review.paper_order_created ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_write_allowed ? "broker write allowed" : "broker write blocked", review.broker_write_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.live_capital_enabled ? "live capital enabled" : "live capital disabled", review.live_capital_enabled ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Policy score", formatProbability(review.policy_score))}
                    ${renderMetric("Venue", htmlText(review.selected_venue, "none"))}
                    ${renderMetric("Venue mode", htmlText(review.venue_mode, "disabled"))}
                    ${renderMetric("Reviewed", formatTime(review.reviewed_at))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Kill switches</p>
                    <div class="tag-row">${renderTagList(killSwitchTags, "No kill switches recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Execution checks</p>
                    <div class="tag-row">${renderTagList(checkTags, "No execution checks recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Blocked reasons</p>
                    <div class="tag-row">${renderTagList(review.blocked_reasons, "No blocking reason recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <ul class="status-list">${asArray(review.required_next_steps).length
                        ? asArray(review.required_next_steps).map((step) => `<li><strong>${htmlText(step)}</strong></li>`).join("")
                        : "<li><strong>No next steps recorded</strong></li>"
                    }</ul>
                </section>
            </article>
        `;
    };

    const renderStagedPaperOrderCard = (review) => {
        const checkTags = Object.entries(review.reconciliation_checks || {}).map(([key, value]) => `${key}: ${value}`);
        const hypothetical = review.hypothetical_order || {};
        return `
            <article class="trade-intent-card ${statusClass(review.status || "blocked_before_staging")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "blocked_before_staging")}
                    <p class="label">Staged paper-order contract · ${htmlText(review.source_execution_policy_review_id, "execution review pending")}</p>
                </div>
                <h3>${htmlText(review.instrument, "Staged paper-order review")}</h3>
                <p>${htmlText(review.boundary, "Staged paper-order contract is disabled.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(review.execution_allowed ? "execution allowed" : "execution blocked", review.execution_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.staged_paper_order_created ? "staged order created" : "no staged order created", review.staged_paper_order_created ? "blocked" : "online")}
                    ${renderInlineBadge(review.paper_order_submittable ? "paper order submittable" : "paper order not submittable", review.paper_order_submittable ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_write_allowed ? "broker write allowed" : "broker write blocked", review.broker_write_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.live_capital_enabled ? "live capital enabled" : "live capital disabled", review.live_capital_enabled ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Venue", htmlText(review.selected_venue, "none"))}
                    ${renderMetric("Venue mode", htmlText(review.venue_mode, "disabled"))}
                    ${renderMetric("Account", htmlText(review.account_scope, "trial"))}
                    ${renderMetric("Hypothetical", htmlText(hypothetical.status, "not created"))}
                    ${renderMetric("Notional", formatMoney(hypothetical.notional_gbp))}
                    ${renderMetric("Reviewed", formatTime(review.reviewed_at))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Hypothetical order</p>
                    <div class="tag-row">
                        ${renderInlineBadge(`direction: ${dashboardText(hypothetical.direction, "not determined")}`, "pending")}
                        ${renderInlineBadge(`type: ${dashboardText(hypothetical.order_type, "not applicable")}`, "pending")}
                        ${renderInlineBadge(`idempotency: ${dashboardText(hypothetical.idempotency_key, "not allocated")}`, "blocked")}
                        ${renderInlineBadge(`event log: ${dashboardText(hypothetical.event_log_ref, "not written")}`, "blocked")}
                    </div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Reconciliation checks</p>
                    <div class="tag-row">${renderTagList(checkTags, "No reconciliation checks recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Blocked reasons</p>
                    <div class="tag-row">${renderTagList(review.blocked_reasons, "No blocking reason recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <ul class="status-list">${asArray(review.required_next_steps).length
                        ? asArray(review.required_next_steps).map((step) => `<li><strong>${htmlText(step)}</strong></li>`).join("")
                        : "<li><strong>No next steps recorded</strong></li>"
                    }</ul>
                </section>
            </article>
        `;
    };

    const renderBrokerReconciliationCard = (review) => {
        const checkTags = Object.entries(review.reconciliation_checks || {}).map(([key, value]) => `${key}: ${value}`);
        const brokerEcho = review.broker_echo || {};
        const hypothetical = review.hypothetical_order || {};
        return `
            <article class="trade-intent-card ${statusClass(review.status || "blocked_before_broker_reconciliation")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "blocked_before_broker_reconciliation")}
                    <p class="label">Broker reconciliation contract · ${htmlText(review.source_staged_paper_order_review_id, "staged review pending")}</p>
                </div>
                <h3>${htmlText(review.instrument, "Broker reconciliation review")}</h3>
                <p>${htmlText(review.boundary, "Broker reconciliation is read-only and cannot submit paper orders.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(review.idempotency_key_allocated ? "idempotency allocated" : "idempotency not allocated", review.idempotency_key_allocated ? "blocked" : "online")}
                    ${renderInlineBadge(review.event_log_prewrite_created ? "Event Log prewrite created" : "Event Log prewrite not created", review.event_log_prewrite_created ? "blocked" : "online")}
                    ${renderInlineBadge(review.duplicate_order_guard_ready ? "duplicate guard ready" : "duplicate guard not ready", review.duplicate_order_guard_ready ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_echo_verified ? "broker echo verified" : "broker echo not verified", review.broker_echo_verified ? "blocked" : "online")}
                    ${renderInlineBadge(review.paper_order_submit_allowed ? "paper submit allowed" : "paper submit blocked", review.paper_order_submit_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_write_allowed ? "broker write allowed" : "broker write blocked", review.broker_write_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.live_capital_enabled ? "live capital enabled" : "live capital disabled", review.live_capital_enabled ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Venue", htmlText(review.selected_venue, "none"))}
                    ${renderMetric("Mode", htmlText(review.venue_mode, "disabled"))}
                    ${renderMetric("Account", htmlText(review.account_scope, "trial"))}
                    ${renderMetric("Hypothetical", htmlText(hypothetical.status, "not created"))}
                    ${renderMetric("Broker echo", htmlText(brokerEcho.status, "not requested"))}
                    ${renderMetric("Reviewed", formatTime(review.reviewed_at))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Broker echo</p>
                    <div class="tag-row">
                        ${renderInlineBadge(`adapter: ${dashboardText(brokerEcho.adapter, "not selected")}`, "pending")}
                        ${renderInlineBadge(`venue: ${dashboardText(brokerEcho.venue, "none")}`, "pending")}
                        ${renderInlineBadge(`client id: ${dashboardText(brokerEcho.client_order_id, "not allocated")}`, "blocked")}
                        ${renderInlineBadge(`external id: ${dashboardText(brokerEcho.external_order_id, "not created")}`, "blocked")}
                        ${renderInlineBadge(`ack: ${dashboardText(brokerEcho.ack_status, "not available")}`, "blocked")}
                        ${renderInlineBadge(`fill: ${dashboardText(brokerEcho.fill_status, "not available")}`, "blocked")}
                    </div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Reconciliation checks</p>
                    <div class="tag-row">${renderTagList(checkTags, "No broker reconciliation checks recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Blocked reasons</p>
                    <div class="tag-row">${renderTagList(review.blocked_reasons, "No blocking reason recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <ul class="status-list">${asArray(review.required_next_steps).length
                        ? asArray(review.required_next_steps).map((step) => `<li><strong>${htmlText(step)}</strong></li>`).join("")
                        : "<li><strong>No next steps recorded</strong></li>"
                    }</ul>
                </section>
            </article>
        `;
    };

    const renderPaperSubmitReceiptCard = (review) => {
        const checkTags = Object.entries(review.receipt_checks || {}).map(([key, value]) => `${key}: ${value}`);
        const receipt = review.simulated_receipt || {};
        const brokerEcho = review.broker_echo || {};
        const idempotency = review.idempotency_design || {};
        const prewrite = review.event_log_prewrite_schema || {};
        const snapshot = review.pre_trade_snapshot_schema || {};
        const duplicateGuard = review.duplicate_order_guard || {};
        return `
            <article class="trade-intent-card ${statusClass(review.status || "blocked_before_dry_run_submit")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(review.status || "blocked_before_dry_run_submit")}
                    <p class="label">Dry-run paper-submit receipt · ${htmlText(review.source_broker_reconciliation_review_id, "broker review pending")}</p>
                </div>
                <h3>${htmlText(review.instrument, "Paper-submit receipt review")}</h3>
                <p>${htmlText(review.boundary, "Paper-submit receipt is dry-run only and cannot call brokers.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(review.dry_run_receipt_created ? "dry-run receipt created" : "dry-run receipt not created", review.dry_run_receipt_created ? "pending" : "online")}
                    ${renderInlineBadge(review.paper_order_submitted ? "paper order submitted" : "paper order not submitted", review.paper_order_submitted ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_post_called ? "broker POST called" : "broker POST not called", review.broker_post_called ? "blocked" : "online")}
                    ${renderInlineBadge(review.broker_write_allowed ? "broker write allowed" : "broker write blocked", review.broker_write_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(review.live_capital_enabled ? "live capital enabled" : "live capital disabled", review.live_capital_enabled ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Venue", htmlText(review.selected_venue, "none"))}
                    ${renderMetric("Mode", htmlText(review.venue_mode, "disabled"))}
                    ${renderMetric("Account", htmlText(review.account_scope, "trial"))}
                    ${renderMetric("Receipt", htmlText(receipt.status, "not created"))}
                    ${renderMetric("Broker echo", htmlText(brokerEcho.status, "not requested"))}
                    ${renderMetric("Submitted", htmlText(review.submitted_at, "not submitted"))}
                    ${renderMetric("Reviewed", formatTime(review.reviewed_at))}
                </div>
                <section class="trade-check-section">
                    <p class="label">Simulated receipt</p>
                    <div class="tag-row">
                        ${renderInlineBadge(`mode: ${dashboardText(receipt.mode, "dry run only")}`, "pending")}
                        ${renderInlineBadge(`adapter: ${dashboardText(receipt.adapter, "not selected")}`, "pending")}
                        ${renderInlineBadge(`client id: ${dashboardText(receipt.client_order_id, "not allocated")}`, "blocked")}
                        ${renderInlineBadge(`preview: ${dashboardText(receipt.idempotency_preview_key || idempotency.preview_key, "not designed")}`, "pending")}
                        ${renderInlineBadge(`external id: ${dashboardText(receipt.external_order_id, "not created")}`, "blocked")}
                        ${renderInlineBadge(receipt.broker_post_called ? "POST called" : "POST not called", receipt.broker_post_called ? "blocked" : "online")}
                    </div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Idempotency preview</p>
                    <div class="tag-row">
                        ${renderInlineBadge(`status: ${dashboardText(idempotency.status, "not designed")}`, "pending")}
                        ${renderInlineBadge(`key: ${dashboardText(idempotency.preview_key, "not allocated")}`, "pending")}
                        ${renderInlineBadge(idempotency.broker_usable ? "broker usable" : "not broker usable", idempotency.broker_usable ? "blocked" : "online")}
                        ${renderInlineBadge(idempotency.allocation_authority ? "allocation authority" : "no allocation authority", idempotency.allocation_authority ? "blocked" : "online")}
                    </div>
                    <p class="mini">${htmlText(idempotency.boundary, "Idempotency design is dry-run only.")}</p>
                </section>
                <section class="trade-check-section">
                    <p class="label">Prewrite and duplicate guard</p>
                    <div class="tag-row">
                        ${renderInlineBadge(`prewrite: ${dashboardText(prewrite.status, "not defined")}`, "pending")}
                        ${renderInlineBadge(prewrite.write_performed ? "Event Log written" : "Event Log not written", prewrite.write_performed ? "blocked" : "online")}
                        ${renderInlineBadge(`snapshot: ${dashboardText(snapshot.status, "not defined")}`, "pending")}
                        ${renderInlineBadge(snapshot.capture_performed ? "snapshot captured" : "snapshot not captured", snapshot.capture_performed ? "blocked" : "online")}
                        ${renderInlineBadge(`duplicate guard: ${dashboardText(duplicateGuard.status, "not defined")}`, "pending")}
                        ${renderInlineBadge(duplicateGuard.lookup_performed ? "duplicate lookup run" : "duplicate lookup not run", duplicateGuard.lookup_performed ? "blocked" : "online")}
                        ${renderInlineBadge(duplicateGuard.guard_write_performed ? "guard written" : "guard not written", duplicateGuard.guard_write_performed ? "blocked" : "online")}
                    </div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Receipt checks</p>
                    <div class="tag-row">${renderTagList(checkTags, "No paper-submit receipt checks recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Blocked reasons</p>
                    <div class="tag-row">${renderTagList(review.blocked_reasons, "No blocking reason recorded")}</div>
                </section>
                <section class="trade-check-section">
                    <p class="label">Required next steps</p>
                    <ul class="status-list">${asArray(review.required_next_steps).length
                        ? asArray(review.required_next_steps).map((step) => `<li><strong>${htmlText(step)}</strong></li>`).join("")
                        : "<li><strong>No next steps recorded</strong></li>"
                    }</ul>
                </section>
            </article>
        `;
    };

    const renderSignalReviewCard = (record) => {
        const chain = record.decision_chain || {};
        const requiredSteps = asArray(signalReview.required_chain_steps);
        const orderedSteps = requiredSteps.length ? requiredSteps : Object.keys(chain);
        const governanceAction = record.governance_action || {};
        const chainRows = orderedSteps.length
            ? orderedSteps.map((stepKey) => {
                const step = chain[stepKey] || {};
                return `
                    <li>
                        <strong>${htmlText(step.label, stepKey)}</strong>
                        <span>${htmlText(step.display_status || step.backend_status, "not exported")} · ${htmlText(step.stage, "stage unknown")}</span>
                        <small>${htmlText(step.detail, "No backend detail exported.")} · backend ${htmlText(step.backend_status, "unknown")} · UI inferred ${step.ui_inferred ? "true" : "false"} · ${literalHtmlText(step.source_artifact_id, "source artifact not exported")}</small>
                    </li>
                `;
            }).join("")
            : `
                <li>
                    <strong>No decision chain</strong>
                    <span>The backend did not export Q5-12 chain steps.</span>
                </li>
            `;
        return `
            <article class="trade-intent-card ${statusClass(record.status || "blocked")}">
                <div class="cognition-card-head">
                    ${renderStatusPill(record.status || "blocked")}
                    <p class="label">Signal Review · backend decision chain</p>
                </div>
                <h3>${htmlText(record.strategy_family_key, "Strategy family")}</h3>
                <p>${htmlText(record.boundary || signalReview.boundary, "Q5-12 Signal Review is read-only.")}</p>
                <div class="tag-row">
                    ${renderInlineBadge(record.backend_truth_displayed ? "backend truth displayed" : "backend truth missing", record.backend_truth_displayed ? "online" : "blocked")}
                    ${renderInlineBadge(record.ui_inferred_readiness ? "UI inferred readiness" : "no UI-inferred readiness", record.ui_inferred_readiness ? "blocked" : "online")}
                    ${renderInlineBadge(record.trade_approval_control_enabled ? "approval control enabled" : "no approval control", record.trade_approval_control_enabled ? "blocked" : "online")}
                    ${renderInlineBadge(record.order_place_control_enabled ? "order control enabled" : "no order control", record.order_place_control_enabled ? "blocked" : "online")}
                    ${renderInlineBadge(record.broker_write_allowed ? "broker write enabled" : "no broker write", record.broker_write_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(record.live_capital_enabled ? "live capital enabled" : "live capital disabled", record.live_capital_enabled ? "blocked" : "online")}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Instrument", record.primary_instrument || "unknown")}
                    ${renderMetric("Venue", record.selected_venue || "none")}
                    ${renderMetric("Chain", `${orderedSteps.length} steps`)}
                    ${renderMetric("Target", governanceAction.target_artifact_stage || "not linked")}
                </div>
                <section class="trade-check-section">
                    <p class="label">Decision chain</p>
                    <ul class="status-list">${chainRows}</ul>
                </section>
                <section class="trade-check-section">
                    <p class="label">Governance comment</p>
                    <div class="tag-row">
                        ${renderInlineBadge(governanceAction.comment_event_log_written ? "comment event logged" : "comment event missing", governanceAction.comment_event_log_written ? "online" : "blocked")}
                        <span class="inline-badge ${statusClass(governanceAction.target_artifact_id ? "online" : "blocked")}">target ${literalHtmlText(governanceAction.target_artifact_id, "not linked")}</span>
                        ${renderInlineBadge(governanceAction.trade_approval_control_enabled ? "approval authority" : "no approval control", governanceAction.trade_approval_control_enabled ? "blocked" : "online")}
                        ${renderInlineBadge(governanceAction.order_place_control_enabled ? "order authority" : "no order control", governanceAction.order_place_control_enabled ? "blocked" : "online")}
                    </div>
                    <p class="mini">${htmlText(governanceAction.comment_text, "No governance comment text exported.")}</p>
                </section>
                <section class="trade-check-section">
                    <p class="label">Kill-switch action</p>
                    <div class="tag-row">
                        ${renderInlineBadge(governanceAction.kill_switch_action_available ? "kill-switch action available" : "kill-switch action unavailable", governanceAction.kill_switch_action_available ? "pending" : "blocked")}
                        <span class="inline-badge ${statusClass(governanceAction.kill_switch_mutation_authority ? "blocked" : "online")}">mode ${literalHtmlText(governanceAction.kill_switch_action_mode, "not exported")}</span>
                        ${renderInlineBadge(governanceAction.kill_switch_action_event_log_written ? "kill-switch action event logged" : "kill-switch action event missing", governanceAction.kill_switch_action_event_log_written ? "online" : "blocked")}
                        ${renderInlineBadge(governanceAction.kill_switch_mutation_authority ? "mutates switch state" : "no kill-switch mutation", governanceAction.kill_switch_mutation_authority ? "blocked" : "online")}
                    </div>
                    <p class="mini">${htmlText(governanceAction.boundary, "Governance actions are Event Log only.")}</p>
                </section>
            </article>
        `;
    };

    const observedSignals = asArray(tradeLayer.watching);
    const candidates = asArray(tradeLayer.candidates);
    const blocked = asArray(tradeLayer.blocked);

    const observedHtml = observedSignals.length
        ? observedSignals.map(renderObservedSignalCard).join("")
        : `<article class="trade-intent-card"><h3>No observed signals</h3><p>No TradingView or source-derived observed signal is present in the local snapshot.</p></article>`;

    const candidatesHtml = candidates.length
        ? candidates.map((intent) => renderTradeIntentCard(intent, "pending")).join("")
        : `<article class="trade-intent-card"><h3>No candidates</h3><p>No structured candidate is present in the local Trade Intent Store.</p></article>`;

    const blockedHtml = blocked.length
        ? blocked.map((intent) => renderTradeIntentCard(intent, "blocked")).join("")
        : `<article class="trade-intent-card"><h3>No blocked trades</h3><p>No blocked trade record is present yet.</p></article>`;

    const signalReviewHtml = signalReviewRecords.length
        ? signalReviewRecords.map(renderSignalReviewCard).join("")
        : `<article class="trade-intent-card"><h3>No Signal Review records</h3><p>Q5-12 has not exported backend decision-chain records yet.</p></article>`;

    const renderPaperTradeDrillStep = (record) => `
        <article class="trade-intent-card ${statusClass(record.step_passed ? "online" : "blocked")}">
            <div class="cognition-card-head">
                ${renderStatusPill(record.display_status || record.backend_status || "blocked")}
                <p class="label">Q5-14 · ${htmlText(record.source_key, "source")}</p>
            </div>
            <h3>${htmlText(record.step_label || record.step_key, "Paper trade drill step")}</h3>
            <p>${htmlText(record.blocked_reason || "Backend state matches display state.")}</p>
            <div class="summary-strip compact">
                ${renderMetric("Step", record.step_order || 0)}
                ${renderMetric("Metric", record.backend_metric_name || "not exported")}
                ${renderMetric("Value", record.backend_metric_value ?? 0)}
                ${renderMetric("Backend", record.backend_status || "blocked")}
                ${renderMetric("Display", record.display_status || "blocked")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(record.display_derived_from_backend ? "backend-derived" : "display inferred", record.display_derived_from_backend ? "online" : "blocked")}
                ${renderInlineBadge(record.ui_inferred_readiness ? "UI inferred readiness" : "no UI inference", record.ui_inferred_readiness ? "blocked" : "online")}
                ${renderInlineBadge(record.broker_post_called ? "broker POST called" : "no broker POST", record.broker_post_called ? "blocked" : "online")}
                ${renderInlineBadge(record.live_capital_enabled ? "live capital enabled" : "live capital disabled", record.live_capital_enabled ? "blocked" : "online")}
                ${renderInlineBadge(record.phase7_proof_credit_allowed ? "paper growth maturity open" : "no false growth maturity", record.phase7_proof_credit_allowed ? "blocked" : "online")}
            </div>
        </article>
    `;

    const paperTradeDrillHtml = paperTradeDrillRecords.length
        ? paperTradeDrillRecords.map(renderPaperTradeDrillStep).join("")
        : `<article class="trade-intent-card"><h3>No Q5-14 drill records</h3><p>The end-to-end paper trade drill has not exported backend step records yet.</p></article>`;

    const renderPhase5CertificationGate = (record) => `
        <article class="trade-intent-card">
            <div class="trade-card-topline">
                ${renderStatusPill(record.display_status || record.backend_status || "blocked")}
                <p class="label">${htmlText(record.source_stage || "Q5")} certification input</p>
            </div>
            <h3>${htmlText(record.label || record.artifact_key, "Certification gate")}</h3>
            <p>${record.gate_passed ? "Backend gate passed." : htmlText(asArray(record.failed_conditions).join(", ") || "Gate is blocked by backend state.")}</p>
            <div class="summary-strip compact">
                ${renderMetric("Source status", record.source_status || "unknown")}
                ${renderMetric("Validation errors", record.validation_error_count || 0)}
                ${renderMetric("Recorded", record.recorded ? "yes" : "no")}
                ${renderMetric("Backend", record.backend_status || "blocked")}
                ${renderMetric("Display", record.display_status || "blocked")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(record.display_derived_from_backend ? "backend-derived" : "display inferred", record.display_derived_from_backend ? "online" : "blocked")}
                ${renderInlineBadge(record.ui_inferred_readiness ? "UI inferred readiness" : "no UI inference", record.ui_inferred_readiness ? "blocked" : "online")}
                ${renderInlineBadge(record.phase7_proof_credit_allowed ? "paper growth maturity open" : "no false growth maturity", record.phase7_proof_credit_allowed ? "blocked" : "online")}
            </div>
        </article>
    `;

    const phase5CertificationHtml = phase5CertificationGates.length
        ? phase5CertificationGates.map(renderPhase5CertificationGate).join("")
        : `<article class="trade-intent-card"><h3>No Q5-15 certification gates</h3><p>Phase 5 certification has not exported backend gate records yet.</p></article>`;

    const phase6SourceStatusHtml = asArray(phase6LearningLoop.source_status_records).length
        ? asArray(phase6LearningLoop.source_status_records).map((record) => `
            <li>
                <strong>${htmlText(record.source_stage || record.source_key, "Phase 6 source")}</strong>
                <span>${htmlText(record.display_status || record.backend_status || "not_run")} · backend ${htmlText(record.backend_status || "not_run")}</span>
                <small>${record.display_derived_from_backend ? "backend-derived" : "display inferred"} · UI inferred ${record.ui_inferred_readiness ? "true" : "false"} · ${htmlText(record.source_ref, "source ref withheld")}</small>
            </li>
        `).join("")
        : `<li><strong>No Q6-16 source records</strong><span>The Learning Loop visibility artifact has not exported source records yet.</span></li>`;

    const phase7SourceStatusHtml = asArray(phase7DemoProof.source_status_records).length
        ? asArray(phase7DemoProof.source_status_records).map((record) => `
            <li>
                <strong>${htmlText(record.source_stage || record.source_key, "Paper growth source")}</strong>
                <span>${htmlText(record.display_status || record.backend_status || "not_run")} · backend ${htmlText(record.backend_status || "not_run")}</span>
                <small>${record.display_derived_from_backend ? "backend-derived" : "display inferred"} · UI inferred ${record.ui_inferred_readiness ? "true" : "false"} · ${htmlText(record.source_ref, "source ref withheld")}</small>
            </li>
        `).join("")
        : `<li><strong>No paper growth source records</strong><span>The paper growth visibility artifact has not exported source records yet.</span></li>`;

    const orderStateHtml = rows.slice(3).map(([label, items]) => `
        <li>
            <strong>${htmlText(label)}</strong>
            <span>${items.length ? `${items.length} records` : "not connected yet"}</span>
        </li>
    `).join("");

    target.innerHTML = `
        ${renderTradeLifecycleWorkspace(tradesModel)}
        <section class="trade-consolidated-snapshot ${statusClass(blocked.length ? "blocked" : (candidates.length ? "pending" : "online"))}" data-trade-consolidated-snapshot>
            <div>
                <p class="label">Consolidated trade readout</p>
                <h3>${htmlText(tradesModel.summary)}</h3>
                <p>${htmlText(tradeLayer.boundary, "No broker order path exists. A trade idea is not an order.")}</p>
            </div>
            <div class="trade-consolidated-metrics">
                ${renderMetric("Observed signals", observedSignals.length)}
                ${renderMetric("Candidates", candidates.length)}
                ${renderMetric("Blocked trades", blocked.length)}
                ${renderMetric("Submitted paper", tradesModel.counts.submitted_paper_order)}
                ${renderMetric("Closed paper", tradesModel.counts.closed_paper_trade)}
                ${renderMetric("Postmortems due", tradesModel.counts.postmortem_due)}
            </div>
            <div class="tag-row">
                ${renderInlineBadge("Candidate is not order", "pending")}
                ${renderInlineBadge(`store ${summary.status || tradeLayer.store_status || "unknown"}`, tradeLayer.store_status === "ok" ? "online" : "degraded")}
                ${renderInlineBadge(`${summary.intent_count || 0} local records`, summary.intent_count ? "online" : "pending")}
                ${renderInlineBadge(`${summary.execution_allowed_count || 0} execution allowed`, summary.execution_allowed_count ? "blocked" : "online")}
                ${renderInlineBadge(`${summary.paper_order_allowed_count || 0} paper orders allowed`, summary.paper_order_allowed_count ? "blocked" : "online")}
            </div>
        </section>
        <div class="trade-diagnostic-groups" data-trade-diagnostic-groups>
            <details class="trade-review-group" open data-trade-review-group="proof_lifecycle">
                <summary>
                    <strong>Paper trade lifecycle</strong>
                    <span>Paper drill, certification, learning, and paper growth visibility live together here.</span>
                </summary>
                <div class="trade-review-group-body">
        <section class="trade-intent-section" data-phase5-paper-trade-drill>
            <p class="label">Q5-14 End-To-End Paper Trade Drill</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", paperTradeDrill.status || "not_run")}
                ${renderMetric("State", paperTradeDrill.paper_trade_drill_state || "not_run")}
                ${renderMetric("Steps", paperTradeDrill.step_count || 0)}
                ${renderMetric("Blockers", paperTradeDrill.blocker_count || 0)}
                ${renderMetric("Exit gate", paperTradeDrill.phase5_paper_trade_drill_exit_gate_passed ? "passed" : "blocked")}
                ${renderMetric("Complete", paperTradeDrill.paper_trade_drill_complete ? "yes" : "no")}
                ${renderMetric("Event Log", paperTradeDrill.event_log_written ? "written" : "missing")}
            </div>
            <div class="summary-strip compact">
                ${renderMetric("Approval", paperTradeDrill.paper_submit_approval_present ? "present" : (paperTradeDrill.paper_submit_approval_state || "missing"))}
                ${renderMetric("Submit path", paperTradeDrill.paper_submit_path_available_count || 0)}
                ${renderMetric("Submitted", paperTradeDrill.submitted_paper_order_count || 0)}
                ${renderMetric("Open", paperTradeDrill.open_position_count || 0)}
                ${renderMetric("Closed", paperTradeDrill.closed_trade_count || 0)}
                ${renderMetric("Postmortem due", paperTradeDrill.postmortem_due_count || 0)}
                ${renderMetric("Broker POST", paperTradeDrill.broker_post_called_count || 0)}
                ${renderMetric("Live capital", paperTradeDrill.live_capital_enabled_count || 0)}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(paperTradeDrill.phase5_paper_trade_drill_implementation_ready ? "implementation ready" : "implementation pending", paperTradeDrill.phase5_paper_trade_drill_implementation_ready ? "online" : "pending")}
                ${renderInlineBadge(paperTradeDrill.paper_submit_approval_present ? "paper-submit approval present" : "paper-submit approval missing", paperTradeDrill.paper_submit_approval_present ? "online" : "blocked")}
                ${renderInlineBadge((paperTradeDrill.paper_submit_path_available_count || 0) ? `paper submit path available · paper submit path ${paperTradeDrill.paper_submit_path_available_count || 0}` : `paper submit path blocked · paper submit path ${paperTradeDrill.paper_submit_path_available_count || 0}`, (paperTradeDrill.paper_submit_path_available_count || 0) ? "online" : "blocked")}
                ${renderInlineBadge((paperTradeDrill.broker_post_called_count || 0) ? "broker POST recorded" : "no broker POST", (paperTradeDrill.broker_post_called_count || 0) ? "blocked" : "online")}
                ${renderInlineBadge((paperTradeDrill.live_capital_enabled_count || 0) ? "live capital enabled" : "live capital disabled", (paperTradeDrill.live_capital_enabled_count || 0) ? "blocked" : "online")}
                <span class="sr-only">no Phase 7 proof credit</span>
            </div>
            <div class="tag-row">${renderTagList(paperTradeDrill.blockers, "No Q5-14 blockers exported")}</div>
            <p class="mini">${htmlText(paperTradeDrill.boundary, "Q5-14 is approval-gated and cannot call brokers or enable live capital.")}</p>
            <div class="trade-intent-stack">${paperTradeDrillHtml}</div>
        </section>
        <section class="trade-intent-section" data-phase5-certification>
            <p class="label">Q5-15 Phase 5 Certification</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", phase5Certification.status || "not_run")}
                ${renderMetric("Stage", phase5Certification.stage_status || "not_run")}
                ${renderMetric("Certified", phase5Certification.phase5_certified ? "yes" : "no")}
                ${renderMetric("Exit gate", phase5Certification.phase5_exit_gate ? "passed" : "blocked")}
                ${renderMetric("Passed gates", phase5Certification.input_gate_passed_count || 0)}
                ${renderMetric("Blocked gates", phase5Certification.input_gate_blocked_count || 0)}
                ${renderMetric("Blockers", phase5Certification.certification_blocker_count || 0)}
                ${renderMetric("Event Log", phase5Certification.event_log_written ? "written" : "missing")}
            </div>
            <div class="summary-strip compact">
                ${renderMetric("Paper drill", phase5Certification.paper_trade_drill_complete ? "complete" : "incomplete")}
                ${renderMetric("Submitted", phase5Certification.submitted_paper_order_count || 0)}
                ${renderMetric("Open", phase5Certification.open_position_count || 0)}
                ${renderMetric("Closed", phase5Certification.closed_trade_count || 0)}
                ${renderMetric("Phase 6", phase5Certification.phase6_handoff_allowed ? "allowed" : "blocked")}
                ${renderMetric("Paper growth plan", phase5Certification.phase7_planning_allowed ? "allowed" : "blocked")}
                ${renderMetric("Proof credit", phase5Certification.phase7_proof_credit_allowed ? "allowed" : "blocked")}
                ${renderMetric("Live capital", phase5Certification.live_capital_enabled_count || 0)}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(phase5Certification.phase5_certified ? "Phase 5 certified" : "Phase 5 not certified", phase5Certification.phase5_certified ? "online" : "blocked")}
                ${renderInlineBadge(phase5Certification.paper_trade_drill_exit_gate_passed ? "Q5-14 exit passed" : "Q5-14 exit blocked", phase5Certification.paper_trade_drill_exit_gate_passed ? "online" : "blocked")}
                ${renderInlineBadge(phase5Certification.phase6_handoff_allowed ? "Phase 6 handoff allowed" : "Phase 6 handoff blocked", phase5Certification.phase6_handoff_allowed ? "online" : "blocked")}
                ${renderInlineBadge(phase5Certification.phase7_proof_credit_allowed ? "paper growth maturity allowed" : "no false growth maturity", phase5Certification.phase7_proof_credit_allowed ? "blocked" : "online")}
                ${renderInlineBadge((phase5Certification.live_capital_enabled_count || 0) ? "live capital enabled" : "live capital disabled", (phase5Certification.live_capital_enabled_count || 0) ? "blocked" : "online")}
            </div>
            <div class="tag-row">${renderTagList(phase5Certification.certification_blockers, "No Q5-15 blockers exported")}</div>
            <p class="mini">${htmlText(phase5Certification.boundary, "Q5-15 cannot bypass Q5-14 or enable live capital.")}</p>
            <div class="trade-intent-stack">${phase5CertificationHtml}</div>
        </section>
        <section class="trade-intent-section" data-phase5-phase6-handoff>
            <p class="label">Q5E-10 Phase 6 Handoff Closeout</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", phase5Phase6Handoff.status || "not_run")}
                ${renderMetric("State", phase5Phase6Handoff.handoff_state || "not_run")}
                ${renderMetric("Phase 6 plan", phase5Phase6Handoff.phase6_learning_loop_plan_allowed ? "allowed" : "blocked")}
                ${renderMetric("Implementation", phase5Phase6Handoff.phase6_learning_loop_implementation_allowed ? "allowed" : "blocked")}
                ${renderMetric("Learning writes", phase5Phase6Handoff.phase6_learning_write_allowed ? "allowed" : "blocked")}
                ${renderMetric("Required modules", phase5Phase6Handoff.phase6_required_module_count || 0)}
                ${renderMetric("Blockers", phase5Phase6Handoff.blocker_count || 0)}
                ${renderMetric("Event Log", phase5Phase6Handoff.event_log_written ? "written" : "missing")}
            </div>
            <div class="summary-strip compact">
                ${renderMetric("Certified", phase5Phase6Handoff.phase5_certified ? "yes" : "no")}
                ${renderMetric("Q5-14 exit", phase5Phase6Handoff.paper_trade_drill_exit_gate_passed ? "passed" : "blocked")}
                ${renderMetric("Closed trades", phase5Phase6Handoff.closed_trade_count || 0)}
                ${renderMetric("Postmortem due", phase5Phase6Handoff.postmortem_due_count || 0)}
                ${renderMetric("Source errors", phase5Phase6Handoff.source_validation_error_count || 0)}
                ${renderMetric("Proof credit", phase5Phase6Handoff.phase7_proof_credit_allowed ? "allowed" : "blocked")}
                ${renderMetric("Live capital", phase5Phase6Handoff.live_capital_enabled_count || 0)}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(phase5Phase6Handoff.phase6_learning_loop_plan_allowed ? "Phase 6 plan allowed" : "Phase 6 plan blocked", phase5Phase6Handoff.phase6_learning_loop_plan_allowed ? "online" : "blocked")}
                ${renderInlineBadge(phase5Phase6Handoff.phase6_learning_loop_implementation_allowed ? "Phase 6 implementation allowed" : "Phase 6 implementation blocked", phase5Phase6Handoff.phase6_learning_loop_implementation_allowed ? "blocked" : "online")}
                ${renderInlineBadge(phase5Phase6Handoff.phase6_knowledge_graph_write_allowed ? "knowledge graph writes allowed" : "knowledge graph writes blocked", phase5Phase6Handoff.phase6_knowledge_graph_write_allowed ? "blocked" : "online")}
                ${renderInlineBadge(phase5Phase6Handoff.phase7_proof_credit_allowed ? "paper growth maturity allowed" : "no false growth maturity", phase5Phase6Handoff.phase7_proof_credit_allowed ? "blocked" : "online")}
                ${renderInlineBadge((phase5Phase6Handoff.live_capital_enabled_count || 0) ? "live capital enabled" : "live capital disabled", (phase5Phase6Handoff.live_capital_enabled_count || 0) ? "blocked" : "online")}
            </div>
            <div class="tag-row">${renderTagList(phase5Phase6Handoff.phase6_required_modules, "No Phase 6 module requirements exported")}</div>
            <div class="tag-row">${renderTagList(phase5Phase6Handoff.blockers, "No Q5E-10 blockers exported")}</div>
            <p class="mini">${htmlText(phase5Phase6Handoff.boundary, "Q5E-10 is a Phase 6 planning gate only and cannot write learning data.")}</p>
            <p class="mini">Next: ${htmlText(phase5Phase6Handoff.recommended_next_stage, "Q6-0 Phase 6 re-entry and learning-loop implementation plan")}</p>
        </section>
        <section class="trade-intent-section" data-phase6-learning-loop>
            <p class="label">Q6-16 Learning Loop Journal Visibility</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", phase6LearningLoop.status || "not_run")}
                ${renderMetric("State", phase6LearningLoop.learning_state || "not_run")}
                ${renderMetric("Approval", phase6LearningLoop.approval_state || "not_requested")}
                ${renderMetric("Postmortem due", phase6LearningLoop.postmortem_due_count || 0)}
                ${renderMetric("Resolved", phase6LearningLoop.postmortem_resolved_count || 0)}
                ${renderMetric("Backend parity", `${phase6LearningLoop.backend_parity_error_count || 0} errors`)}
                ${renderMetric("UI inferred", phase6LearningLoop.ui_inferred_readiness_count || 0)}
                ${renderMetric("Event Log", phase6LearningLoop.event_log_written ? "written" : "missing")}
            </div>
            <div class="summary-strip compact">
                ${renderMetric("Graph staged", phase6LearningLoop.staged_graph_entry_count || 0)}
                ${renderMetric("Graph read", phase6LearningLoop.knowledge_graph_read_result_count || 0)}
                ${renderMetric("Model proposals", phase6LearningLoop.model_weight_proposal_count || 0)}
                ${renderMetric("Trust proposals", phase6LearningLoop.trust_score_proposal_count || 0)}
                ${renderMetric("Replay variants", phase6LearningLoop.shadow_replay_variant_count || 0)}
                ${renderMetric("Architect proposals", phase6LearningLoop.architect_recommendation_count || 0)}
                ${renderMetric("Blocked recs", phase6LearningLoop.architect_blocked_recommendation_count || 0)}
                ${renderMetric("Blocked auth", phase6LearningLoop.blocked_authority_count || 0)}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(phase6LearningLoop.backend_derived ? "backend-derived" : "not backend-derived", phase6LearningLoop.backend_derived ? "online" : "blocked")}
                ${renderInlineBadge(phase6LearningLoop.display_derived_from_backend ? "display derived from backend" : "display inferred", phase6LearningLoop.display_derived_from_backend ? "online" : "blocked")}
                ${renderInlineBadge((phase6LearningLoop.phase6_learning_write_allowed || phase6LearningLoop.phase6_knowledge_graph_write_allowed) ? "learning writes open" : "learning writes blocked", (phase6LearningLoop.phase6_learning_write_allowed || phase6LearningLoop.phase6_knowledge_graph_write_allowed) ? "blocked" : "online")}
                ${renderInlineBadge(phase6LearningLoop.phase6_model_weight_update_allowed ? "model updates open" : "model updates blocked", phase6LearningLoop.phase6_model_weight_update_allowed ? "blocked" : "online")}
                ${renderInlineBadge(phase6LearningLoop.phase6_trust_score_update_allowed ? "trust updates open" : "trust updates blocked", phase6LearningLoop.phase6_trust_score_update_allowed ? "blocked" : "online")}
                ${renderInlineBadge(phase6LearningLoop.phase6_architect_policy_mutation_allowed ? "policy mutation open" : "policy mutation blocked", phase6LearningLoop.phase6_architect_policy_mutation_allowed ? "blocked" : "online")}
                ${renderInlineBadge(phase6LearningLoop.phase7_proof_credit_allowed ? "paper growth maturity open" : "no false growth maturity", phase6LearningLoop.phase7_proof_credit_allowed ? "blocked" : "online")}
                ${renderInlineBadge(phase6LearningLoop.live_capital_enabled ? "live capital enabled" : "live capital disabled", phase6LearningLoop.live_capital_enabled ? "blocked" : "online")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(`${phase6LearningLoop.raw_payload_exposed_count || 0} raw payload exposures`, phase6LearningLoop.raw_payload_exposed_count ? "blocked" : "online")}
                ${renderInlineBadge(`${phase6LearningLoop.local_path_exposed_count || 0} local path exposures`, phase6LearningLoop.local_path_exposed_count ? "blocked" : "online")}
                ${renderInlineBadge(`${phase6LearningLoop.secret_ref_exposed_count || 0} secret refs`, phase6LearningLoop.secret_ref_exposed_count ? "blocked" : "online")}
                ${renderInlineBadge(`${phase6LearningLoop.broker_identifier_exposed_count || 0} broker ids`, phase6LearningLoop.broker_identifier_exposed_count ? "blocked" : "online")}
                ${renderInlineBadge(`${phase6LearningLoop.unsafe_write_counter_total || 0} unsafe writes`, phase6LearningLoop.unsafe_write_counter_total ? "blocked" : "online")}
            </div>
            <ul class="status-list">${phase6SourceStatusHtml}</ul>
            <div class="tag-row">${renderTagList(phase6LearningLoop.blocked_authorities, "No blocked-authority ledger exported")}</div>
            <p class="mini">${htmlText(phase6LearningLoop.boundary, "Q6-16 is backend-derived visibility only and cannot infer readiness or mutate learning state.")}</p>
            <p class="mini">Next: ${htmlText(phase6LearningLoop.recommended_next_stage, "Q6-17 Phase 6 Certification")}</p>
        </section>
        <section class="trade-intent-section" data-phase6-certification>
            <p class="label">Q6-17 Phase 6 Certification</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", phase6Certification.status || "not_run")}
                ${renderMetric("State", phase6Certification.certification_state || "not_run")}
                ${renderMetric("Certified", phase6Certification.phase6_certified ? "yes" : "no")}
                ${renderMetric("Exit gate", phase6Certification.phase6_exit_gate ? "passed" : "blocked")}
                ${renderMetric("Paper growth plan", phase6Certification.phase7_demo_proof_planning_allowed ? "allowed" : "blocked")}
                ${renderMetric("Proof credit", phase6Certification.phase7_proof_credit_allowed ? "allowed" : "blocked")}
                ${renderMetric("Passed gates", phase6Certification.input_gate_passed_count || 0)}
                ${renderMetric("Blocked gates", phase6Certification.input_gate_blocked_count || 0)}
            </div>
            <div class="summary-strip compact">
                ${renderMetric("Blockers", phase6Certification.certification_blocker_count || 0)}
                ${renderMetric("Postmortem due", phase6Certification.postmortem_due_count || 0)}
                ${renderMetric("Unresolved", phase6Certification.unresolved_postmortem_count || 0)}
                ${renderMetric("Approval", phase6Certification.approval_state || "not_requested")}
                ${renderMetric("Pending actions", phase6Certification.pending_review_action_count || 0)}
                ${renderMetric("KG read", phase6Certification.knowledge_graph_read_result_count || 0)}
                ${renderMetric("Model proposals", phase6Certification.model_weight_proposal_count || 0)}
                ${renderMetric("Trust proposals", phase6Certification.trust_score_proposal_count || 0)}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(phase6Certification.phase6_certified ? "Phase 6 certified" : "Phase 6 not certified", phase6Certification.phase6_certified ? "online" : "blocked")}
                ${renderInlineBadge(phase6Certification.reviewed_postmortem_coverage_satisfied ? "postmortems reviewed/deferred" : "postmortems unresolved", phase6Certification.reviewed_postmortem_coverage_satisfied ? "online" : "blocked")}
                ${renderInlineBadge(phase6Certification.learning_actions_review_satisfied ? "learning review done" : "learning approval pending", phase6Certification.learning_actions_review_satisfied ? "online" : "blocked")}
                ${renderInlineBadge(phase6Certification.knowledge_graph_requirement_satisfied ? "KG requirement satisfied" : "KG blocked pending approval", phase6Certification.knowledge_graph_requirement_satisfied ? "online" : "blocked")}
                ${renderInlineBadge(phase6Certification.phase7_demo_proof_planning_allowed ? "paper growth planning allowed" : "paper growth planning blocked", phase6Certification.phase7_demo_proof_planning_allowed ? "online" : "blocked")}
                ${renderInlineBadge(phase6Certification.phase7_proof_credit_allowed ? "paper growth maturity allowed" : "no false growth maturity", phase6Certification.phase7_proof_credit_allowed ? "blocked" : "online")}
                ${renderInlineBadge(phase6Certification.phase5_test_trades_count_for_phase7 ? "Phase 5 trades count for proof" : "Phase 5 trades excluded from proof", phase6Certification.phase5_test_trades_count_for_phase7 ? "blocked" : "online")}
                ${renderInlineBadge(phase6Certification.live_capital_enabled ? "live capital enabled" : "live capital disabled", phase6Certification.live_capital_enabled ? "blocked" : "online")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(`${phase6Certification.unsafe_write_counter_total || 0} unsafe writes`, phase6Certification.unsafe_write_counter_total ? "blocked" : "online")}
                ${renderInlineBadge(`${phase6Certification.blocking_unsafe_count || 0} blocking unsafe counts`, phase6Certification.blocking_unsafe_count ? "blocked" : "online")}
                ${renderInlineBadge(`${phase6Certification.broker_write_allowed_count || 0} broker writes`, phase6Certification.broker_write_allowed_count ? "blocked" : "online")}
                ${renderInlineBadge(`${phase6Certification.live_capital_enabled_count || 0} live-capital grants`, phase6Certification.live_capital_enabled_count ? "blocked" : "online")}
            </div>
            <div class="tag-row">${renderTagList(phase6Certification.certification_blockers, "No Q6-17 blockers exported")}</div>
            <p class="mini">${htmlText(phase6Certification.boundary, "Q6-17 is a certification gate only and cannot approve learning or enable live capital.")}</p>
            <p class="mini">Next: ${htmlText(phase6Certification.recommended_next_stage, "Resolve or explicitly defer Q6 learning approval")}</p>
        </section>
        <section class="trade-intent-section" data-phase7-demo-proof>
            <p class="label">Paper Growth Trial Visibility</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", phase7DemoProof.status || "not_run")}
                ${renderMetric("State", phase7DemoProof.proof_state || "not_run")}
                ${renderMetric("Day", `${phase7DemoProof.completed_calendar_day_count || 0}/${phase7DemoProof.phase7_harness_day_count || 30}`)}
                ${renderMetric("Week", `${phase7DemoProof.current_proof_week_number || 0}/${phase7DemoProof.proof_week_count || 0}`)}
                ${renderMetric("Qualified", phase7DemoProof.qualified_setup_count || 0)}
                ${renderMetric("Missed setups", phase7DemoProof.missed_qualified_setup_count || 0)}
                ${renderMetric("Proof target", phase7DemoProof.weekly_proof_trade_target || 3)}
                ${renderMetric("Event Log", phase7DemoProof.event_log_written ? "written" : "missing")}
            </div>
            <div class="summary-strip compact">
                ${renderMetric("Staged", phase7DemoProof.staged_proof_order_count || 0)}
                ${renderMetric("Submitted", phase7DemoProof.submitted_paper_order_count || 0)}
                ${renderMetric("Broker receipts", phase7DemoProof.broker_receipt_count || 0)}
                ${renderMetric("Mirrored", phase7DemoProof.mirrored_submitted_order_count || 0)}
                ${renderMetric("Open", phase7DemoProof.open_position_count || 0)}
                ${renderMetric("Closed", phase7DemoProof.closed_proof_trade_count || 0)}
                ${renderMetric("Postmortem due", phase7DemoProof.postmortem_due_count || 0)}
                ${renderMetric("Decision chains", `${phase7DemoProof.complete_decision_chain_count || 0}/${(phase7DemoProof.complete_decision_chain_count || 0) + (phase7DemoProof.missing_decision_chain_count || 0)}`)}
            </div>
            <div class="summary-strip compact">
                ${renderMetric("Expectancy", phase7DemoProof.expectancy_after_costs_gbp == null ? "no sample" : formatMoney(phase7DemoProof.expectancy_after_costs_gbp))}
                ${renderMetric("Drawdown", phase7DemoProof.drawdown_within_cap ? "within cap" : "breached")}
                ${renderMetric("Observed DD", phase7DemoProof.max_drawdown_fraction_observed == null ? "no sample" : formatProbability(phase7DemoProof.max_drawdown_fraction_observed))}
                ${renderMetric("Overrides", phase7DemoProof.override_count || 0)}
                ${renderMetric("Maturity", `${phase7DemoProof.closed_proof_trade_count || 0}/${phase7DemoProof.mature_benchmark || 100}`)}
                ${renderMetric("Remaining", phase7DemoProof.closed_trades_remaining_to_mature || 100)}
                ${renderMetric("Weekly review", phase7DemoProof.q7_16_weekly_review_pack_stage_allowed ? "allowed" : "blocked")}
                ${renderMetric("Live capital", phase7DemoProof.live_capital_enabled ? "enabled" : "disabled")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(phase7DemoProof.backend_derived ? "backend-derived" : "not backend-derived", phase7DemoProof.backend_derived ? "online" : "blocked")}
                ${renderInlineBadge(phase7DemoProof.display_derived_from_backend ? "display derived from backend" : "display inferred", phase7DemoProof.display_derived_from_backend ? "online" : "blocked")}
                ${renderInlineBadge((phase7DemoProof.ui_inferred_readiness_count || 0) ? "UI inferred readiness" : "no UI inference", phase7DemoProof.ui_inferred_readiness_count ? "blocked" : "online")}
                ${renderInlineBadge(phase7DemoProof.phase5_test_trades_count_for_phase7 ? "Phase 5 trades count for proof" : "Phase 5 trades excluded from proof", phase7DemoProof.phase5_test_trades_count_for_phase7 ? "blocked" : "online")}
                ${renderInlineBadge(phase7DemoProof.phase7_proof_credit_allowed ? "paper growth maturity open" : "no false growth maturity", phase7DemoProof.phase7_proof_credit_allowed ? "blocked" : "online")}
                ${renderInlineBadge(phase7DemoProof.live_capital_enabled ? "live capital enabled" : "live capital disabled", phase7DemoProof.live_capital_enabled ? "blocked" : "online")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(phase7DemoProof.phase7_statistical_immaturity_hidden ? "statistical immaturity hidden" : "statistical immaturity visible", phase7DemoProof.phase7_statistical_immaturity_hidden ? "blocked" : "online")}
                ${renderInlineBadge(phase7DemoProof.phase7_mature_benchmark_met ? "verified maturity met" : "verified maturity not met", phase7DemoProof.phase7_mature_benchmark_met ? "online" : "pending")}
                ${renderInlineBadge(phase7DemoProof.sample_contaminated ? "sample contaminated" : "sample clean", phase7DemoProof.sample_contaminated ? "blocked" : "online")}
                ${renderInlineBadge(phase7DemoProof.new_proof_trades_frozen ? "new proof trades frozen" : "new proof trades not frozen", phase7DemoProof.new_proof_trades_frozen ? "blocked" : "online")}
                ${renderInlineBadge(`${phase7DemoProof.broker_post_called_count || 0} broker paper POST calls`, phase7DemoProof.broker_post_called_count ? "pending" : "online")}
                ${renderInlineBadge(`${phase7DemoProof.alpaca_post_called_count || 0} Alpaca paper POST calls`, phase7DemoProof.alpaca_post_called_count ? "pending" : "online")}
                ${renderInlineBadge(`${phase7DemoProof.unsafe_write_counter_total || 0} unsafe writes`, phase7DemoProof.unsafe_write_counter_total ? "blocked" : "online")}
            </div>
            <ul class="status-list">${phase7SourceStatusHtml}</ul>
            <div class="tag-row">${renderTagList(phase7DemoProof.blockers, "No Q7-15 blockers exported")}</div>
            <p class="mini">${htmlText(phase7DemoProof.boundary, "Q7-15 is backend-derived visibility only and cannot infer readiness or enable live capital.")}</p>
            <p class="mini">Next: ${htmlText(phase7DemoProof.recommended_next_stage, "Q7-16 Weekly Review Pack")}</p>
        </section>
                </div>
            </details>
            <details class="trade-review-group" data-trade-review-group="gate_chain">
                <summary>
                    <strong>Gate chain and broker readiness</strong>
                    <span>Signal review, risk, execution policy, staging, reconciliation, and dry-run receipt diagnostics.</span>
                </summary>
                <div class="trade-review-group-body">
        <section class="trade-intent-section" data-phase5-signal-review>
            <p class="label">Signal Review UI and governance actions</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", signalReview.status || "not_run")}
                ${renderMetric("Records", signalReview.signal_review_record_count || 0)}
                ${renderMetric("Decision chain", signalReview.decision_chain_count || 0)}
                ${renderMetric("Governance comments", signalReview.governance_comment_event_count || 0)}
                ${renderMetric("Kill-switch actions", signalReview.kill_switch_action_event_count || 0)}
                ${renderMetric("Backend truth", signalReview.backend_truth_displayed_count || 0)}
                ${renderMetric("UI inferred", signalReview.ui_inferred_readiness_count || 0)}
                ${renderMetric("Event Log", signalReview.event_log_written ? "written" : "missing")}
            </div>
            <div class="tag-row">
                ${renderInlineBadge(`${signalReview.trade_approval_control_enabled_count || 0} approval controls`, signalReview.trade_approval_control_enabled_count ? "blocked" : "online")}
                ${renderInlineBadge(`${signalReview.order_place_control_enabled_count || 0} order controls`, signalReview.order_place_control_enabled_count ? "blocked" : "online")}
                ${renderInlineBadge(`${signalReview.position_resize_control_enabled_count || 0} resize controls`, signalReview.position_resize_control_enabled_count ? "blocked" : "online")}
                ${renderInlineBadge(`${signalReview.position_close_control_enabled_count || 0} close controls`, signalReview.position_close_control_enabled_count ? "blocked" : "online")}
                ${renderInlineBadge(`${signalReview.order_cancel_control_enabled_count || 0} cancel controls`, signalReview.order_cancel_control_enabled_count ? "blocked" : "online")}
                ${renderInlineBadge(`${signalReview.broker_write_allowed_count || 0} broker writes`, signalReview.broker_write_allowed_count ? "blocked" : "online")}
                ${renderInlineBadge(`${signalReview.prediction_market_write_allowed_count || 0} prediction-market writes`, signalReview.prediction_market_write_allowed_count ? "blocked" : "online")}
                ${renderInlineBadge(`${signalReview.live_capital_enabled_count || 0} live-capital grants`, signalReview.live_capital_enabled_count ? "blocked" : "online")}
            </div>
            <p class="mini">${htmlText(signalReview.boundary, "Q5-12 Signal Review is read-only and can only write Event Log governance notes.")}</p>
            <div class="trade-intent-stack">${signalReviewHtml}</div>
        </section>
        <section id="trade-risk-policy" class="trade-intent-section">
            <p class="label">Risk Agent policy router</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", riskAgent.status || "pending")}
                ${renderMetric("Reviews", riskAgent.review_count || 0)}
                ${renderMetric("Blocked", riskAgent.by_status?.blocked_before_risk || 0)}
                ${renderMetric("Policy hold", riskAgent.by_status?.policy_hold || 0)}
                ${renderMetric("Shadow ready", riskAgent.by_status?.risk_shadow_ready || 0)}
                ${renderMetric("Orders", riskAgent.order_created_count || 0)}
                ${renderMetric("Broker writes", riskAgent.broker_write_allowed_count || 0)}
                ${renderMetric("Max risk", `${htmlText(riskAgent.max_risk_pct_per_idea, "1")}%`)}
            </div>
            <p class="mini">${htmlText(riskAgent.boundary, "Risk Agent policy router is read-only and cannot approve risk or create orders.")}</p>
            <div class="trade-intent-stack">${riskReviews.length
                ? riskReviews.map(renderRiskReviewCard).join("")
                : `<article class="trade-intent-card"><h3>No Risk Agent reviews yet</h3><p>The policy router has not reviewed any signal or trade-intent records.</p></article>`
            }</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Execution Policy and kill switches</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", executionPolicy.status || "pending")}
                ${renderMetric("Reviews", executionPolicy.review_count || 0)}
                ${renderMetric("Policy blocks", executionPolicy.by_status?.blocked_by_policy || 0)}
                ${renderMetric("Kill-switch holds", executionPolicy.by_status?.kill_switch_hold || 0)}
                ${renderMetric("Shadow ready", executionPolicy.by_status?.paper_order_shadow_ready || 0)}
                ${renderMetric("Staged orders", executionPolicy.staged_paper_order_allowed_count || 0)}
                ${renderMetric("Orders created", executionPolicy.paper_order_created_count || 0)}
                ${renderMetric("Broker writes", executionPolicy.broker_write_allowed_count || 0)}
                ${renderMetric("Live capital", executionPolicy.live_capital_enabled_count || 0)}
            </div>
            <p class="mini">${htmlText(executionPolicy.boundary, "Execution policy is read-only and cannot stage paper orders or write to brokers.")}</p>
            <div class="trade-intent-stack">${executionPolicyReviews.length
                ? executionPolicyReviews.map(renderExecutionPolicyCard).join("")
                : `<article class="trade-intent-card"><h3>No execution policy reviews yet</h3><p>The execution-policy layer has not reviewed any Risk Agent records.</p></article>`
            }</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Disabled staged paper-order contract</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", stagedPaperOrder.status || "pending")}
                ${renderMetric("Reviews", stagedPaperOrder.review_count || 0)}
                ${renderMetric("Blocked", stagedPaperOrder.by_status?.blocked_before_staging || 0)}
                ${renderMetric("Reconciliation hold", stagedPaperOrder.by_status?.reconciliation_hold || 0)}
                ${renderMetric("Disabled hold", stagedPaperOrder.by_status?.disabled_contract_hold || 0)}
                ${renderMetric("Staged created", stagedPaperOrder.staged_paper_order_created_count || 0)}
                ${renderMetric("Submittable", stagedPaperOrder.paper_order_submittable_count || 0)}
                ${renderMetric("Broker writes", stagedPaperOrder.broker_write_allowed_count || 0)}
                ${renderMetric("Live capital", stagedPaperOrder.live_capital_enabled_count || 0)}
            </div>
            <p class="mini">${htmlText(stagedPaperOrder.boundary, "Staged paper-order contract is disabled and read-only.")}</p>
            <div class="trade-intent-stack">${stagedPaperOrderReviews.length
                ? stagedPaperOrderReviews.map(renderStagedPaperOrderCard).join("")
                : `<article class="trade-intent-card"><h3>No staged paper-order reviews yet</h3><p>The disabled staging contract has not reviewed any Execution Policy records.</p></article>`
            }</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Read-only broker reconciliation</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", brokerReconciliation.status || "pending")}
                ${renderMetric("Reviews", brokerReconciliation.review_count || 0)}
                ${renderMetric("Blocked", brokerReconciliation.by_status?.blocked_before_broker_reconciliation || 0)}
                ${renderMetric("Route closed", brokerReconciliation.by_status?.broker_route_closed || 0)}
                ${renderMetric("Contract hold", brokerReconciliation.by_status?.reconciliation_contract_hold || 0)}
                ${renderMetric("Idempotency", brokerReconciliation.idempotency_key_allocated_count || 0)}
                ${renderMetric("Prewrite", brokerReconciliation.event_log_prewrite_created_count || 0)}
                ${renderMetric("Duplicate guard", brokerReconciliation.duplicate_order_guard_ready_count || 0)}
                ${renderMetric("Broker echo", brokerReconciliation.broker_echo_verified_count || 0)}
                ${renderMetric("Submit", brokerReconciliation.paper_order_submit_allowed_count || 0)}
                ${renderMetric("Broker writes", brokerReconciliation.broker_write_allowed_count || 0)}
                ${renderMetric("Live capital", brokerReconciliation.live_capital_enabled_count || 0)}
            </div>
            <p class="mini">${htmlText(brokerReconciliation.boundary, "Broker reconciliation is read-only and cannot submit paper orders.")}</p>
            <div class="trade-intent-stack">${brokerReconciliationReviews.length
                ? brokerReconciliationReviews.map(renderBrokerReconciliationCard).join("")
                : `<article class="trade-intent-card"><h3>No broker reconciliation reviews yet</h3><p>The broker gate has not reviewed any staged paper-order records.</p></article>`
            }</div>
        </section>
        <section id="trade-broker-receipts" class="trade-intent-section">
            <p class="label">Dry-run paper-submit receipt</p>
            <div class="summary-strip compact">
                ${renderMetric("Status", paperSubmitReceipt.status || "pending")}
                ${renderMetric("Reviews", paperSubmitReceipt.review_count || 0)}
                ${renderMetric("Blocked", paperSubmitReceipt.by_status?.blocked_before_dry_run_submit || 0)}
                ${renderMetric("Dry-run blocked", paperSubmitReceipt.by_status?.dry_run_receipt_blocked || 0)}
                ${renderMetric("Dry-run ready", paperSubmitReceipt.by_status?.dry_run_receipt_ready || 0)}
                ${renderMetric("Receipts", paperSubmitReceipt.dry_run_receipt_created_count || 0)}
                ${renderMetric("Submitted", paperSubmitReceipt.paper_order_submitted_count || 0)}
                ${renderMetric("Broker POST", paperSubmitReceipt.broker_post_called_count || 0)}
                ${renderMetric("Broker writes", paperSubmitReceipt.broker_write_allowed_count || 0)}
                ${renderMetric("Live capital", paperSubmitReceipt.live_capital_enabled_count || 0)}
            </div>
            <p class="mini">${htmlText(paperSubmitReceipt.boundary, "Paper-submit receipt is dry-run only and cannot call brokers.")}</p>
            <div class="trade-intent-stack">${paperSubmitReceiptReviews.length
                ? paperSubmitReceiptReviews.map(renderPaperSubmitReceiptCard).join("")
                : `<article class="trade-intent-card"><h3>No dry-run paper-submit reviews yet</h3><p>The dry-run receipt gate has not reviewed any broker reconciliation records.</p></article>`
            }</div>
        </section>
                </div>
            </details>
            <details class="trade-review-group" data-trade-review-group="signal_records">
                <summary>
                    <strong>Signals, trade ideas, and paper trades</strong>
                    <span>TradingView observations, trade ideas, blocked ideas, and explicit paper lifecycle states.</span>
                </summary>
                <div class="trade-review-group-body">
        <section class="trade-intent-section">
            <p class="label">TradingView MCP technical analysis</p>
            <div class="summary-strip compact">
                ${renderMetric("Connection", tradingViewMcp.connected ? "connected" : "not connected")}
                ${renderMetric("Adapter", tradingViewMcp.status || "degraded")}
                ${renderMetric("Mode", tradingViewMcp.live_calls_enabled ? "live read-only" : "local/sample-safe")}
                ${renderMetric("Contexts", tradingViewMcp.technical_context_count || 0)}
                ${renderMetric("High-conviction flags", tradingViewMcp.obvious_technical_context_count || 0)}
                ${renderMetric("Candidates", `${tradingViewMcp.trade_candidate_creation_allowed ? 1 : 0} created`)}
                ${renderMetric("Paper orders", `${tradingViewMcp.paper_order_allowed ? 1 : 0} allowed`)}
                ${renderMetric("Broker writes", `${tradingViewMcp.broker_write_allowed ? 1 : 0} allowed`)}
            </div>
            <div class="tag-row">
                ${renderInlineBadge("observes and analyses", tradingViewMcp.connected ? "online" : "pending")}
                ${renderInlineBadge("Qadam governs", "online")}
                ${renderInlineBadge("Alpaca Paper executes", "pending")}
                ${renderInlineBadge("no direct trade authority", "online")}
            </div>
            <p class="mini">${htmlText(tradingViewMcp.boundary, "TradingView MCP is read-only technical analysis.")}</p>
        </section>
        <section class="trade-intent-section">
            <p class="label">TradingView alert source</p>
            <div class="summary-strip compact">
                ${renderMetric("Receiver", tradingView.receiver_status || "local contract only")}
                ${renderMetric("Dedupe", tradingView.duplicate_protection || "dedupe key")}
                ${renderMetric("Alerts", tradingView.alert_count || 0)}
                ${renderMetric("Latest", formatTime(tradingView.latest_observed_at))}
                ${renderMetric("Execution", `${tradingView.execution_allowed_count || 0} allowed`)}
                ${renderMetric("Paper orders", `${tradingView.paper_order_allowed_count || 0} allowed`)}
                ${renderMetric("Candidates", `${tradingView.trade_candidate_created_count || 0} created`)}
                ${renderMetric("Source state", tradingView.status || "not initialized")}
            </div>
            <p class="mini">${htmlText(tradingView.boundary, "TradingView alerts are observed signals only. D7 has no execution route.")}</p>
        </section>
        <section class="trade-intent-section">
            <p class="label">Trade state ladder</p>
            <ol class="timeline-list">
                <li>Watching · observed signal only</li>
                <li>Considering Trade · candidate, not order</li>
                <li>Blocked · failed evidence, risk, policy, latency, or credential checks</li>
                <li>Preparing Paper Trade · disabled until dry-run receipt and broker contracts pass</li>
                <li>Postmortem · unavailable until closed paper trades exist</li>
            </ol>
        </section>
        <section class="trade-intent-section">
            <p class="label">Observed signals</p>
            <div class="trade-intent-stack">${observedHtml}</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Candidates</p>
            <div class="trade-intent-stack">${candidatesHtml}</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Blocked trades</p>
            <div class="trade-intent-stack">${blockedHtml}</div>
        </section>
        <section class="trade-intent-section">
            <p class="label">Paper lifecycle states</p>
            <ul class="status-list trade-state-list">${orderStateHtml}</ul>
        </section>
                </div>
            </details>
        </div>
    `;
    initTradeLifecycleFilters(target);
}

function renderPerformanceStatusCard(label, value, body, tone = "pending") {
    return `
        <article class="performance-status-card ${statusClass(tone)}">
            <div class="source-workspace-topline">
                ${renderStatusPill(tone)}
                <p class="label">${htmlText(label)}</p>
            </div>
            <h3>${htmlText(value)}</h3>
            <p>${htmlText(body)}</p>
        </article>
    `;
}

function renderPerformanceProgress(label, current, target, fraction, tone = "pending", body = "") {
    const width = Math.round(Math.min(1, Math.max(0, Number(fraction || 0))) * 100);
    return `
        <article class="performance-progress-card ${statusClass(tone)}">
            <div class="performance-progress-head">
                <div>
                    <p class="label">${htmlText(label)}</p>
                    <h3>${htmlText(current)}/${htmlText(target)}</h3>
                </div>
                ${renderInlineBadge(`${width}%`, tone)}
            </div>
            <div class="performance-progress-bar" aria-label="${literalHtmlText(label)} progress">
                <span style="width: ${width}%"></span>
            </div>
            <p>${htmlText(body)}</p>
        </article>
    `;
}

function renderPerformanceSourceRecord(record) {
    return `
        <li>
            <strong>${htmlText(record.stage)} · ${htmlText(record.key)}</strong>
            <span>${htmlText(record.status)} · backend ${htmlText(record.backend_status)}</span>
            <small>${record.event_log_written ? "event log written" : "event log missing"} · ${record.ui_inferred_readiness ? "UI inferred readiness" : "backend-derived"} · ${record.public_safe ? "sanitized" : "not sanitized"}</small>
        </li>
    `;
}

function renderPerformanceWorkspace(model) {
    const demo = model.demo_proof || {};
    const paper = model.paper_account || {};
    const risk = model.risk_state || {};
    const maturity = model.operational_vs_maturity || {};
    const quality = model.proof_quality || {};
    const safety = model.safety_boundary || {};
    const sourceRecords = asArray(quality.source_status_records);
    const sourceHtml = sourceRecords.length
        ? sourceRecords.map(renderPerformanceSourceRecord).join("")
        : `<li><strong>No paper growth source records</strong><span>The backend has not exported paper growth source status records.</span></li>`;
    const dayTone = demo.phase7_30_day_run_complete ? "online" : "pending";
    const drawdownTone = risk.risk_halt_active || !risk.drawdown_within_cap ? "blocked" : "online";
    const maturityTone = maturity.phase7_mature_benchmark_met ? "online" : "pending";
    const forcedTradeTone = safety.forced_trade_pressure_detected ? "blocked" : "online";
    return `
        <section class="performance-workspace" data-performance-workspace>
            <div class="performance-workspace-head">
                <div>
                    <p class="label">Performance workspace</p>
                    <h2>60-day paper growth trial and account performance</h2>
                    <p>${htmlText(model.summary, "Performance state has not loaded.")}</p>
                </div>
                <div class="performance-boundary-card">
                    ${renderInlineBadge("2x paper target over 60 days", "pending")}
                    ${renderInlineBadge("No forced trades", forcedTradeTone)}
                    ${renderInlineBadge("Phase 5 trades excluded", demo.phase5_test_trades_count_for_phase7 ? "blocked" : "online")}
                    ${renderInlineBadge("Verified records only", demo.display_proof_credit_allowed ? "blocked" : "online")}
                    ${renderInlineBadge(risk.live_capital_enabled ? "live capital enabled" : "live capital disabled", risk.live_capital_enabled ? "blocked" : "online")}
                    <p>${htmlText(model.boundary, "Read-only performance view.")}</p>
                </div>
            </div>
            <div class="summary-strip compact performance-summary-strip">
                ${renderMetric("Growth window", `${model.growth_trial?.horizon_days || 60} days`)}
                ${renderMetric("Paper target", formatMoney(model.growth_trial?.target_value_gbp || 200000))}
                ${renderMetric("Target progress", formatPercent(model.growth_trial?.progress_fraction || 0))}
                ${renderMetric("Qualified setups", demo.qualified_setup_count || 0)}
                ${renderMetric("Verified trades", `${demo.closed_proof_trade_count || 0}/${demo.mature_benchmark || 100}`)}
                ${renderMetric("Drawdown", risk.drawdown_within_cap ? "within cap" : "breached")}
                ${renderMetric("Postmortems due", paper.postmortem_due_count || 0)}
                ${renderMetric("Live capital", risk.live_capital_enabled ? "enabled" : "disabled")}
            </div>
            <div class="performance-status-grid">
                ${renderPerformanceProgress(
                    "60-day paper growth target",
                    formatMoney(model.growth_trial?.current_value_gbp || 0),
                    formatMoney(model.growth_trial?.target_value_gbp || 200000),
                    model.growth_trial?.progress_fraction || 0,
                    dayTone,
                    `Target: ${formatMoney(model.growth_trial?.starting_value_gbp || 100000)} to ${formatMoney(model.growth_trial?.target_value_gbp || 200000)} in ${model.growth_trial?.horizon_days || 60} days.`
                )}
                ${renderPerformanceProgress(
                    "Verified performance maturity",
                    maturity.closed_proof_trade_count || 0,
                    maturity.maturity_benchmark || 100,
                    demo.maturity_progress_fraction || 0,
                    maturityTone,
                    "Statistical maturity is tracked separately; it must not create pressure to force trades."
                )}
                ${renderPerformanceStatusCard(
                    "Drawdown and halt state",
                    risk.risk_halt_active ? "Halt active" : (risk.drawdown_within_cap ? "Within cap" : "Breached"),
                    `${dashboardText(risk.drawdown_state, "drawdown unknown")} · observed ${formatProbability(risk.max_drawdown_fraction_observed)} · overrides ${risk.override_count || 0}`,
                    drawdownTone
                )}
                ${renderPerformanceStatusCard(
                    "Trade selectivity",
                    `${demo.current_proof_week_number || 0}/${demo.proof_week_count || 5} weeks`,
                    "Selective larger paper positions only when evidence, strategy, quantum/classical consultation, risk, and Alpaca Paper agree.",
                    "pending"
                )}
                ${renderPerformanceStatusCard(
                    "Setup funnel",
                    `${demo.qualified_setup_count || 0} qualified`,
                    `${demo.candidate_setup_count || 0} candidates · ${demo.eligible_setup_count || 0} eligible · ${demo.missed_qualified_setup_count || 0} missed · ${demo.missed_qualified_setup_unexplained_count || 0} unexplained`,
                    demo.missed_qualified_setup_unexplained_count ? "blocked" : "online"
                )}
                ${renderPerformanceStatusCard(
                    "Paper mirror",
                    formatMoney(paper.current_balance_gbp),
                    `${formatMoney(paper.total_pnl_gbp)} total P&L · ${formatPercent(paper.drawdown_pct)} drawdown · ${paper.closed_paper_trade_count || 0} closed paper trades`,
                    paper.live_capital_enabled || paper.write_authority ? "blocked" : "online"
                )}
            </div>
            <section class="performance-section">
                <div class="performance-section-head">
                    <div>
                        <p class="label">Proof lifecycle</p>
                        <h3>Qualified setup to postmortem trail</h3>
                    </div>
                    ${renderInlineBadge("No forced trade pressure", forcedTradeTone)}
                </div>
                <div class="summary-strip compact">
                    ${renderMetric("Staged", demo.staged_proof_order_count || 0)}
                    ${renderMetric("Submitted", demo.submitted_paper_order_count || 0)}
                    ${renderMetric("Broker receipts", demo.broker_receipt_count || 0)}
                    ${renderMetric("Mirrored", demo.mirrored_submitted_order_count || 0)}
                    ${renderMetric("Open", demo.open_position_count || 0)}
                    ${renderMetric("Closed", demo.closed_proof_trade_count || 0)}
                    ${renderMetric("Postmortem due", demo.postmortem_due_count || 0)}
                    ${renderMetric("Reviewed", demo.postmortem_reviewed_count || 0)}
                </div>
                <div class="tag-row">
                    ${renderInlineBadge(demo.backend_derived ? "backend-derived" : "not backend-derived", demo.backend_derived ? "online" : "blocked")}
                    ${renderInlineBadge(demo.display_derived_from_backend ? "display derived from backend" : "display inferred", demo.display_derived_from_backend ? "online" : "blocked")}
                    ${renderInlineBadge((demo.ui_inferred_readiness_count || 0) ? "UI inferred readiness" : "no UI inference", demo.ui_inferred_readiness_count ? "blocked" : "online")}
                    ${renderInlineBadge(demo.q7_16_weekly_review_pack_stage_allowed ? "weekly review pack allowed" : "weekly review pack blocked", demo.q7_16_weekly_review_pack_stage_allowed ? "online" : "pending")}
                </div>
            </section>
            <section class="performance-section performance-two-col">
                <div>
                    <p class="label">Operational completion vs maturity</p>
                    <dl class="cognition-facts">
                        <div>
                            <dt>Operating run</dt>
                            <dd>${maturity.operational_run_complete ? "30-day run complete" : "30-day run in progress"}</dd>
                        </div>
                        <div>
                            <dt>Maturity</dt>
                            <dd>${htmlText(maturity.maturity_state, "not exported")} · ${maturity.closed_trades_remaining_to_mature || 0} trades remaining to mature</dd>
                        </div>
                        <div>
                            <dt>Immaturity</dt>
                            <dd>${maturity.phase7_statistical_immaturity_hidden ? "hidden" : "visible"} · certification ${maturity.phase7_certification_blocked_by_maturity ? "blocked by maturity" : "not blocked by maturity"}</dd>
                        </div>
                        <div>
                            <dt>Boundary</dt>
                            <dd>${htmlText(maturity.boundary)}</dd>
                        </div>
                    </dl>
                </div>
                <div>
                    <p class="label">Safety counters</p>
                    <div class="tag-row">
                        ${renderInlineBadge(`${safety.broker_post_called_count || 0} broker POST calls`, safety.broker_post_called_count ? "pending" : "online")}
                        ${renderInlineBadge(`${safety.alpaca_post_called_count || 0} Alpaca POST calls`, safety.alpaca_post_called_count ? "pending" : "online")}
                        ${renderInlineBadge(`${safety.unsafe_write_counter_total || 0} unsafe writes`, safety.unsafe_write_counter_total ? "blocked" : "online")}
                        ${renderInlineBadge(`${safety.prediction_market_write_allowed_count || 0} prediction-market writes`, safety.prediction_market_write_allowed_count ? "blocked" : "online")}
                        ${renderInlineBadge(`${safety.crypto_perps_write_allowed_count || 0} crypto-perps writes`, safety.crypto_perps_write_allowed_count ? "blocked" : "online")}
                        ${renderInlineBadge(`${safety.live_capital_enabled_count || 0} live-capital grants`, safety.live_capital_enabled_count ? "blocked" : "online")}
                    </div>
                    <div class="tag-row">${renderTagList(safety.blockers, "No paper growth blockers exported")}</div>
                </div>
            </section>
            <section class="performance-section">
                <div class="performance-section-head">
                    <div>
                        <p class="label">Backend source records</p>
                        <h3>What the Performance workspace is allowed to trust</h3>
                    </div>
                    ${renderInlineBadge(`${quality.source_artifact_count || sourceRecords.length} artifacts`, "pending")}
                </div>
                <ul class="status-list performance-source-list">${sourceHtml}</ul>
            </section>
        </section>
    `;
}

function paperAccountEquityPoints(capital = {}) {
    const curve = asArray(capital.equity_curve)
        .map((point) => ({
            observed_at: point.observed_at || capital.observed_at || null,
            equity_gbp: modelNumber(point.equity_gbp, Number.NaN),
            drawdown_pct: modelNumber(point.drawdown_pct, modelNumber(capital.drawdown_pct, 0)),
            display_currency: point.display_currency || capital.display_currency || capital.account_currency || "GBP"
        }))
        .filter((point) => Number.isFinite(point.equity_gbp));
    if (curve.length) return curve;
    const fallbackEquity = modelNumber(capital.equity_gbp ?? capital.current_balance_gbp, Number.NaN);
    if (!Number.isFinite(fallbackEquity)) return [];
    return [{
        observed_at: capital.observed_at || null,
        equity_gbp: fallbackEquity,
        drawdown_pct: modelNumber(capital.drawdown_pct, 0),
        display_currency: capital.display_currency || capital.account_currency || "GBP"
    }];
}

function paperAccountEquityStats(points = []) {
    const values = points.map((point) => point.equity_gbp).filter(Number.isFinite);
    if (!values.length) {
        return {
            min: 0,
            max: 0,
            first: 0,
            last: 0,
            change: 0,
            change_pct: 0,
            point_count: 0
        };
    }
    const first = values[0];
    const last = values[values.length - 1];
    const change = last - first;
    return {
        min: Math.min(...values),
        max: Math.max(...values),
        first,
        last,
        change,
        change_pct: first ? (change / first) * 100 : 0,
        point_count: values.length
    };
}

function renderPaperAccountEquityChart(capital = {}, points = [], activity = {}) {
    const chartPoints = paperAccountEquityPoints({ ...capital, equity_curve: points });
    const stats = paperAccountEquityStats(chartPoints);
    const currency = capitalCurrency(capital);
    const money = (value) => formatMoney(value, currency);
    const freshnessStatus = dashboardText(capital.mirror_freshness_status, "unknown");
    const freshnessTone = freshnessStatus === "fresh"
        ? "online"
        : (freshnessStatus === "stale" || freshnessStatus === "unknown" ? "degraded" : "pending");
    const reconciliation = capital.portfolio_reconciliation || {};
    const reconciliationStatus = dashboardText(reconciliation.status, capital.broker_reconciliation_status || "not_available");
    const reconciliationTone = reconciliationStatus === "ok"
        ? "online"
        : (/drift|unavailable|missing|unknown|error/i.test(reconciliationStatus) ? "degraded" : "pending");
    const width = 640;
    const height = 220;
    const left = 94;
    const right = 18;
    const top = 20;
    const bottom = 34;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const rawMin = stats.min;
    const rawMax = stats.max;
    const range = rawMax - rawMin;
    const padding = range > 0 ? range * 0.18 : Math.max(10, Math.abs(rawMax || 1000) * 0.01);
    const min = rawMin - padding;
    const max = rawMax + padding;
    const yFor = (value) => top + ((max - value) / (max - min || 1)) * plotHeight;
    const xFor = (index) => left + (chartPoints.length <= 1 ? plotWidth / 2 : (index / (chartPoints.length - 1)) * plotWidth);
    const coordinates = chartPoints.map((point, index) => ({
        ...point,
        x: xFor(index),
        y: yFor(point.equity_gbp)
    }));
    const path = coordinates.length
        ? coordinates.map((point, index) => `${index ? "L" : "M"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(" ")
        : "";
    const area = coordinates.length
        ? `${path} L ${coordinates[coordinates.length - 1].x.toFixed(2)} ${height - bottom} L ${coordinates[0].x.toFixed(2)} ${height - bottom} Z`
        : "";
    const zeroLineY = min <= 0 && max >= 0 ? yFor(0) : null;
    const tone = stats.change < 0 || modelNumber(capital.drawdown_pct, 0) > 0 ? "degraded" : "online";
    const latestLabel = chartPoints.length
        ? `${money(stats.last)} observed ${formatTime(chartPoints[chartPoints.length - 1].observed_at)}`
        : "No equity snapshots available";
    const activityLabels = [
        `${asArray(activity.orders).length} mirrored orders`,
        `${asArray(activity.closedTrades).length} closed trades`,
        `${modelNumber(capital.open_position_count, asArray(capital.open_positions).length)} open positions`
    ];

    if (!chartPoints.length) {
        return `
            <section class="paper-account-section paper-equity-chart-section">
                <div class="performance-section-head">
                    <div>
                        <p class="label">Live paper equity graph</p>
                        <h3>No account curve yet</h3>
                    </div>
                    ${renderInlineBadge("waiting for mirror", "pending")}
                </div>
                <p class="empty-state">The read-only paper-account mirror has not exported balance history yet.</p>
            </section>
        `;
    }

    return `
        <section class="paper-account-section paper-equity-chart-section">
            <div class="performance-section-head">
                <div>
                    <p class="label">Live paper equity graph</p>
                    <h3>${money(stats.last)} in the paper trading account</h3>
                    <p>The line is drawn from local account snapshots. Source of truth is ${htmlText(capital.portfolio_value_source, "paper account mirror")} and the dashboard warns if the broker sync is stale.</p>
                </div>
                <div class="paper-equity-chart-badges">
                    ${renderInlineBadge(`change ${money(stats.change)}`, tone)}
                    ${renderInlineBadge(`${formatPercent(Number(stats.change_pct.toFixed(2)))} from first sample`, tone)}
                    ${renderInlineBadge(`${stats.point_count} snapshots`, "pending")}
                    ${renderInlineBadge(`${currency} display`, "online")}
                    ${renderInlineBadge(capital.mirror_freshness_label || freshnessStatus, freshnessTone)}
                    ${renderInlineBadge(`history check ${reconciliationStatus}`, reconciliationTone)}
                </div>
            </div>
            <div class="paper-source-of-truth ${statusClass(freshnessTone)}">
                <div>
                    <span>Source of truth</span>
                    <strong>${htmlText(capital.portfolio_value_source, "paper mirror")}</strong>
                    <p>Last broker sync ${formatTime(capital.last_broker_sync_at || capital.observed_at)} · age ${htmlText(capital.last_broker_sync_age_seconds == null ? "unknown" : `${Math.round(capital.last_broker_sync_age_seconds / 60)} min`)} · stale after ${htmlText(capital.stale_after_seconds ? `${Math.round(capital.stale_after_seconds / 60)} min` : "unknown")}.</p>
                </div>
                <div>
                    <span>Broker reconciliation</span>
                    <strong>${htmlText(reconciliationStatus)}</strong>
                    <p>${htmlText(reconciliation.detail || "No broker portfolio history reconciliation detail exported.")}</p>
                </div>
            </div>
            <div class="paper-equity-chart-card ${statusClass(tone)}">
                <svg class="paper-equity-chart" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="paper-equity-chart-title paper-equity-chart-desc" preserveAspectRatio="none">
                    <title id="paper-equity-chart-title">Paper trading account equity over time</title>
                    <desc id="paper-equity-chart-desc">${literalHtmlText(latestLabel)}. ${literalHtmlText(activityLabels.join(", "))}.</desc>
                    <line class="chart-grid-line" x1="${left}" y1="${top}" x2="${left}" y2="${height - bottom}"></line>
                    <line class="chart-grid-line" x1="${left}" y1="${height - bottom}" x2="${width - right}" y2="${height - bottom}"></line>
                    <line class="chart-grid-line muted" x1="${left}" y1="${yFor(stats.max).toFixed(2)}" x2="${width - right}" y2="${yFor(stats.max).toFixed(2)}"></line>
                    <line class="chart-grid-line muted" x1="${left}" y1="${yFor(stats.min).toFixed(2)}" x2="${width - right}" y2="${yFor(stats.min).toFixed(2)}"></line>
                    ${zeroLineY === null ? "" : `<line class="chart-grid-line zero" x1="${left}" y1="${zeroLineY.toFixed(2)}" x2="${width - right}" y2="${zeroLineY.toFixed(2)}"></line>`}
                    <path class="paper-equity-area" d="${area}"></path>
                    <path class="paper-equity-line" d="${path}"></path>
                    ${coordinates.map((point) => `
                        <circle class="paper-equity-point" cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="4">
                            <title>${literalHtmlText(`${formatTime(point.observed_at)}: ${money(point.equity_gbp)} equity, ${formatPercent(point.drawdown_pct)} drawdown`)}</title>
                        </circle>
                    `).join("")}
                    <text class="chart-axis-label" x="4" y="${yFor(stats.max).toFixed(2)}">${literalHtmlText(money(stats.max))}</text>
                    <text class="chart-axis-label" x="4" y="${yFor(stats.min).toFixed(2)}">${literalHtmlText(money(stats.min))}</text>
                    <text class="chart-axis-label chart-axis-last" x="${width - right}" y="${height - 8}">${literalHtmlText(formatTime(chartPoints[chartPoints.length - 1].observed_at))}</text>
                </svg>
                <div class="paper-equity-chart-summary">
                    ${renderMetric("Now", money(stats.last))}
                    ${renderMetric("First sample", money(stats.first))}
                    ${renderMetric("High", money(stats.max))}
                    ${renderMetric("Low", money(stats.min))}
                    ${renderMetric("Drawdown", formatPercent(capital.drawdown_pct))}
                    ${renderMetric("Observed", formatTime(capital.observed_at))}
                </div>
                <div class="paper-equity-activity" aria-label="Trade activity represented by the paper-account curve">
                    <strong>Trade activity</strong>
                    ${activityLabels.map((label) => `<span>${htmlText(label)}</span>`).join("")}
                </div>
            </div>
        </section>
    `;
}

function renderCapital(status, viewModels = {}) {
    const target = dashboardQuery("[data-capital]");
    if (!target) return;
    const capital = status.capital || {};
    const phase7DemoProof = status.phase7_demo_proof || {};
    const performance = viewModels?.performance_model || buildPerformanceModel(status);
    const maturityTarget = Number(capital.maturity_closed_trade_target || 100);
    const maturityCount = Number(capital.maturity_closed_trade_count || 0);
    const maturityPct = maturityTarget ? Math.round((maturityCount / maturityTarget) * 100) : 0;
    const safeMaturityPct = Number.isFinite(maturityPct) ? Math.min(100, Math.max(0, maturityPct)) : 0;
    const phase7ProofTarget = Number(phase7DemoProof.mature_benchmark || maturityTarget || 100);
    const phase7ProofCount = Number(phase7DemoProof.closed_proof_trade_count || 0);
    const phase7ProofCreditAllowed = Boolean(phase7DemoProof.phase7_proof_credit_allowed);
    const phase5TradesCountForPhase7 = Boolean(phase7DemoProof.phase5_test_trades_count_for_phase7);
    const openPositions = asArray(capital.open_positions);
    const closedTrades = asArray(capital.closed_trades);
    const orders = asArray(capital.orders);
    const postmortemsDue = asArray(capital.postmortems_due);
    const postmortemsComplete = asArray(capital.postmortems_complete);
    const equityCurve = paperAccountEquityPoints(capital);
    const equityStats = paperAccountEquityStats(equityCurve);
    const totalPnl = modelNumber(capital.realized_pnl_gbp, 0) + modelNumber(capital.unrealized_pnl_gbp, 0);
    const money = (value) => formatCapitalMoney(value, capital);
    const freshnessStatus = dashboardText(capital.mirror_freshness_status, "unknown");
    const freshnessIsStale = freshnessStatus === "stale" || freshnessStatus === "unknown";
    const reconciliationStatus = dashboardText(capital.portfolio_reconciliation?.status, "not_available");
    const reconciliationIsDrift = /drift|error|unavailable|missing|unknown/i.test(reconciliationStatus);
    const accountTone = capital.live_capital_enabled || capital.write_authority
        ? "blocked"
        : (freshnessIsStale || reconciliationIsDrift || modelNumber(capital.drawdown_pct, 0) > 0 || equityStats.change < 0 ? "degraded" : "online");

    const positionRows = openPositions.length
        ? openPositions.map((position) => `
            <li>
                <strong>${htmlText(position.instrument, "Open paper position")}</strong>
                <span>${htmlText(position.direction, "unknown")} · ${money(position.unrealized_pnl_gbp)} unrealized · ${htmlText(position.status, "open")}</span>
                <small>${htmlText(position.quantity, "0")} units · risk ${money(position.risk_size_gbp)} · ${htmlText(position.boundary, "Read-only paper position.")}</small>
            </li>
        `).join("")
        : `<li><strong>No open positions</strong><span>The paper mirror has no open positions.</span></li>`;

    const closedRows = closedTrades.length
        ? closedTrades.map((trade) => `
            <li>
                <strong>${htmlText(trade.instrument, "Closed paper trade")}</strong>
                <span>${money(trade.realized_pnl_gbp)} realized · ${htmlText(trade.postmortem_status, "postmortem state unknown")}</span>
                <small>${htmlText(trade.close_reason, "No close reason")} · ${htmlText(trade.boundary, "Read-only closed trade.")}</small>
            </li>
        `).join("")
        : `<li><strong>No closed trades</strong><span>The paper mirror has no closed paper trades. Paper growth records are tracked separately.</span></li>`;

    const orderRows = orders.length
        ? orders.map((order) => `
            <li>
                <strong>${htmlText(order.instrument, "Mirrored paper order")}</strong>
                <span>${htmlText(order.status, "unknown")} · ${htmlText(order.direction, "unknown")} · ${htmlText(order.order_type, "order")}</span>
                <small>${htmlText(order.quantity, "0")} units · notional ${money(order.notional_gbp)} · ${htmlText(order.boundary, "Read-only mirrored order.")}</small>
            </li>
        `).join("")
        : `<li><strong>No mirrored paper orders</strong><span>Alpaca returned no recent paper orders on the read-only mirror.</span></li>`;

    const curveRows = equityCurve.length
        ? equityCurve.slice(-5).map((point) => `
            <li>
                <strong>${formatTime(point.observed_at)}</strong>
                <span>${money(point.equity_gbp)} equity · ${htmlText(point.drawdown_pct, "0")}% drawdown</span>
            </li>
        `).join("")
        : `<li><strong>No equity snapshots</strong><span>The mirror has not written an account snapshot yet.</span></li>`;

    target.innerHTML = `
        ${renderPerformanceWorkspace(performance)}
        <section class="paper-account-live-board" aria-label="Paper trading account balance">
            <article class="paper-account-balance-card ${statusClass(accountTone)}">
                <span>Paper trading account</span>
                <strong>${money(equityStats.last || capital.current_balance_gbp)}</strong>
                <p>${money(capital.cash_gbp)} cash · ${money(totalPnl)} total P&amp;L · ${formatPercent(capital.drawdown_pct)} drawdown</p>
            </article>
            <article class="paper-account-balance-card">
                <span>Broker sync</span>
                <strong>${htmlText(capital.mirror_freshness_label, "No broker sync")}</strong>
                <p>${htmlText(capital.connection_status, "not connected")} · observed ${formatTime(capital.last_broker_sync_at || capital.observed_at)}</p>
            </article>
            <article class="paper-account-balance-card">
                <span>Currency and history check</span>
                <strong>${htmlText(capitalCurrency(capital))} · ${htmlText(reconciliationStatus)}</strong>
                <p>${htmlText(capital.portfolio_value_source, "paper account mirror")} · history delta ${money(capital.portfolio_reconciliation?.delta || 0)}</p>
            </article>
            <article class="paper-account-balance-card">
                <span>Trading activity</span>
                <strong>${orders.length} orders · ${openPositions.length} open</strong>
                <p>${closedTrades.length} closed paper trades · ${postmortemsDue.length} postmortems due</p>
            </article>
        </section>
        ${renderPaperAccountEquityChart(capital, equityCurve, { orders, closedTrades })}
        ${renderPanelBrief({
            id: "money",
            question: "Is the paper account proving or losing trust?",
            state: money(equityStats.last || capital.current_balance_gbp),
            tone: accountTone,
            primary: `${money(capital.realized_pnl_gbp)} realized, ${money(capital.unrealized_pnl_gbp)} unrealized, ${formatPercent(capital.drawdown_pct)} drawdown, ${maturityCount}/${maturityTarget} closed paper trades, and ${phase7ProofCount}/${phase7ProofTarget} verified paper growth trades.`,
            secondary: `${capital.mirror_freshness_label || "Broker mirror freshness unknown"} · history check ${reconciliationStatus} · open exposure, drawdown, stale paper-mirror timestamps, closed paper trades without postmortems, and paper growth maturity tracked separately.`,
            boundary: capital.boundary || "Read-only paper account mirror. No funding authority and no live broker-write authority."
        })}
        <div class="summary-strip">
            ${renderMetric("Starting", money(capital.starting_balance_gbp))}
            ${renderMetric("Current", money(capital.current_balance_gbp))}
            ${renderMetric("Cash", money(capital.cash_gbp))}
            ${renderMetric("Equity", money(capital.equity_gbp))}
            ${renderMetric("Realized", money(capital.realized_pnl_gbp))}
            ${renderMetric("Unrealized", money(capital.unrealized_pnl_gbp))}
            ${renderMetric("Drawdown", formatPercent(capital.drawdown_pct))}
            ${renderMetric("Closed trades", `${maturityCount}/${maturityTarget}`)}
        </div>
        <p class="empty-state">${htmlText(capital.boundary, "Read-only paper account mirror.")}</p>
        <div class="paper-account-meta">
            ${renderInlineBadge(`mirror ${capital.mirror_status || "unknown"}`, capital.mirror_status === "ok" ? "online" : "degraded")}
            ${renderInlineBadge(capital.account_scope, "online")}
            ${renderInlineBadge(capital.broker, "pending")}
            ${renderInlineBadge(`${capitalCurrency(capital)} display`, "online")}
            ${renderInlineBadge(capital.mirror_freshness_label || freshnessStatus, freshnessIsStale ? "degraded" : "online")}
            ${renderInlineBadge(`history ${reconciliationStatus}`, reconciliationIsDrift ? "degraded" : "online")}
            ${renderInlineBadge(capital.connection_status, capital.mirror_status === "ok" ? "online" : "pending")}
            ${renderInlineBadge(`${capital.write_authority ? "write enabled" : "OK - read-only"}`, capital.write_authority ? "blocked" : "online")}
            ${renderInlineBadge(`${capital.live_capital_enabled ? "live capital" : "OK - paper only"}`, capital.live_capital_enabled ? "blocked" : "online")}
        </div>
        <section class="paper-account-section">
            <p class="label">Paper mirror state</p>
            <div class="summary-strip compact">
                ${renderMetric("Timeline", capital.timeline_status || "not initialized")}
                ${renderMetric("Observed", formatTime(capital.observed_at))}
                ${renderMetric("Last broker sync", formatTime(capital.last_broker_sync_at))}
                ${renderMetric("Sync age", capital.last_broker_sync_age_seconds == null ? "unknown" : `${Math.round(capital.last_broker_sync_age_seconds / 60)} min`)}
                ${renderMetric("Peak equity", money(capital.peak_equity_gbp))}
                ${renderMetric("Max drawdown", formatPercent(capital.max_drawdown_pct))}
                ${renderMetric("History latest", money(capital.portfolio_reconciliation?.history_latest_equity_gbp))}
                ${renderMetric("History delta", money(capital.portfolio_reconciliation?.delta || 0))}
                ${renderMetric("Open positions", capital.open_position_count || openPositions.length)}
                ${renderMetric("Orders", capital.order_count || orders.length)}
                ${renderMetric("Closed trades", capital.closed_trade_count || closedTrades.length)}
                ${renderMetric("Postmortems due", capital.postmortem_due_count || postmortemsDue.length)}
                ${renderMetric("Postmortems complete", capital.postmortem_complete_count || postmortemsComplete.length)}
            </div>
        </section>
        <section class="paper-account-section">
            <p class="label">Maturity benchmark</p>
            <div class="maturity-bar" aria-label="Closed trade maturity progress">
                <span style="width: ${safeMaturityPct}%"></span>
            </div>
            <p class="mini">${maturityCount} of ${maturityTarget} closed paper trades · ${capital.postmortem_complete_count || 0} postmortems complete · ${postmortemsDue.length} due.</p>
            <p class="mini">Verified paper trades: ${phase7ProofCount} of ${phase7ProofTarget} · ${phase7ProofCreditAllowed ? "performance credit allowed" : "no verified performance credit"} · ${phase5TradesCountForPhase7 ? "test trades count for performance" : "test trades excluded from performance"}.</p>
        </section>
        <section class="paper-account-section paper-account-grid">
            <div>
                <p class="label">Open positions</p>
                <ul class="status-list paper-list">${positionRows}</ul>
            </div>
            <div>
                <p class="label">Closed trades</p>
                <ul class="status-list paper-list">${closedRows}</ul>
            </div>
        </section>
        <section class="paper-account-section">
            <p class="label">Mirrored paper orders</p>
            <ul class="status-list paper-list">${orderRows}</ul>
        </section>
        <section class="paper-account-section">
            <p class="label">Equity snapshot log</p>
            <ul class="status-list paper-list">${curveRows}</ul>
        </section>
    `;
}

function renderFundManagerNotes(status, viewModels = {}) {
    const commentsTarget = dashboardQuery("[data-comments-list]");
    const notes = status.fund_manager_notes || {};
    const governance = viewModels?.governance_model || buildGovernanceModel(status);
    const comments = asArray(notes.recent_comments);
    const workspace = dashboardQuery("[data-governance-workspace]");
    if (workspace) {
        workspace.innerHTML = renderGovernanceWorkspace(governance);
    }
    syncGovernanceCommentTargetOptions(governance.comment_targets);
    initGovernanceCommentTargetButtons();
    replacePanelBrief("fund_manager_comments", {
        question: "What should the founding Fund Managers improve?",
        state: `${notes.comment_count || comments.length || 0} notes`,
        tone: notes.implemented_count ? "online" : "pending",
        primary: `${notes.suggestion_count || 0} suggestions, ${notes.accepted_count || 0} accepted, and ${notes.implemented_count || 0} implemented notes are mirrored for governance review.`,
        secondary: "Unlinked comments, accepted/rejected status, implemented suggestions, and notes that should become concrete implementation work.",
        boundary: notes.boundary || "Governance notes only. No trade approval, order placement, or local secret access."
    });

    const summary = dashboardQuery("[data-comments-summary]");
    if (summary) {
        summary.innerHTML = [
            renderMetric("Local notes", notes.comment_count || comments.length || 0),
            renderMetric("Suggestions", notes.suggestion_count || 0),
            renderMetric("Accepted", notes.accepted_count || 0),
            renderMetric("Implemented", notes.implemented_count || 0)
        ].join("");
    }

    setText(
        "[data-comments-boundary]",
        notes.boundary || "Governance notes only. No trade approval, order placement, or local secret access."
    );

    if (!commentsTarget) return;

    commentsTarget.innerHTML = comments.length
        ? comments.map((comment) => `
            <li>
                <strong>${htmlText(comment.target_type, "module")} · ${htmlText(comment.target_key, "general")}</strong>
                <span>${htmlText(comment.body, "No comment body.")}</span>
                <div class="comment-meta">
                    ${renderInlineBadge(comment.status || "suggestion", comment.status || "pending")}
                    ${renderInlineBadge(comment.visibility || notes.visibility || "founding_fund_managers", "online")}
                    ${renderInlineBadge(formatTime(comment.created_at), "pending")}
                </div>
                <small>${htmlText(comment.author_label, "founding_fund_manager")} · ${htmlText(asArray(comment.tags).join(", "), "no tags")}</small>
            </li>
        `).join("")
        : `
            <li>
                <strong>No local comments</strong>
                <span>The local governance mirror has no comments yet.</span>
                <small>${htmlText(notes.browser_write_scope, "comments_only")} · ${htmlText(notes.local_event_log_export, "accepted_or_implemented_only")}</small>
            </li>
        `;
}

function renderConsole(status) {
    const target = dashboardQuery("[data-process-console]");
    if (!target) return;
    const events = asArray(status.process_console);
    const latest = events[events.length - 1] || {};
    replacePanelBrief("process_console", {
        question: "What did Qadam last report about itself?",
        state: `${events.length} events`,
        tone: events.length ? "online" : "pending",
        primary: events.length
            ? `Latest event: ${dashboardText(latest.message, "runtime event")} at ${formatTime(latest.timestamp)}.`
            : "No process events are present in this snapshot yet.",
        secondary: "Stale timestamps, failed exports, fallback-only state, repeated degraded checks, and bridge source changes.",
        boundary: "Read-only event stream. It is not shell access and cannot run commands."
    });
    target.innerHTML = events.length
        ? events.map((event) => `
            <li>
                <time>${formatTime(event.timestamp)}</time>
                <span>${htmlText(event.message)}</span>
            </li>
        `).join("")
        : `<li><time>Now</time><span>No process events in the snapshot yet.</span></li>`;
}

function startDashboardStatusRefresh(session) {
    if (typeof window === "undefined" || typeof window.setInterval !== "function") return;
    window.qadamDashboardStatusSession = session || null;
    if (dashboardStatusRefreshTimer) return;
    dashboardStatusRefreshTimer = window.setInterval(() => {
        if (document.visibilityState && document.visibilityState !== "visible") return;
        renderQadamDashboardStatus(window.qadamDashboardStatusSession).catch((error) => {
            console.error("Qadam dashboard status refresh failed", error);
        });
    }, DASHBOARD_STATUS_REFRESH_MS);
}

async function renderQadamDashboardStatus(session) {
    const banner = dashboardQuery("[data-status-banner]");
    try {
        const { status, source } = await fetchDashboardStatus(session);
        const viewModels = buildQadamDashboardViewModels(status, source);
        if (typeof window !== "undefined") {
            window.qadamDashboardViewModels = viewModels;
        }
        renderSnapshotMeta(status, source);
        renderBalanceTicker(status, viewModels);
        renderDashboardSafetyStrip(status, viewModels);
        renderMissionControl(status, source);
        renderOperatingSummary(status, source);
        renderOverviewFirstScreen(viewModels);
        renderPhase4Strategy(status);
        renderFundModel(status, source);
        renderFlowMap(status, source, viewModels);
        renderWatching(status, viewModels);
        renderCognition(status, viewModels);
        renderWorldview(status);
        renderForbidden(status);
        renderCommunications(status);
        renderTrades(status, viewModels);
        renderCapital(status, viewModels);
        renderFundManagerNotes(status, viewModels);
        renderConsole(status);
        if (document.documentElement) {
            document.documentElement.dataset.dashboardStatus = "rendered";
            document.documentElement.dataset.dashboardStatusSource = source.key;
        }
        startDashboardStatusRefresh(session);
    } catch (error) {
        if (banner) {
            banner.classList.add("snapshot-error");
            banner.innerHTML = `
                <span>Status contract unavailable</span>
                <span>The dashboard shell is loaded, but neither /api/cockpit-status nor /status/cockpit-status.json could be read.</span>
            `;
        }
        if (document.documentElement) {
            document.documentElement.dataset.dashboardStatus = "snapshot-error";
            document.documentElement.dataset.dashboardStatusSource = "unavailable";
        }
        console.error("Qadam dashboard status load failed", error);
    }
}

initCockpitNavigation();
window.activateQadamDashboardView = activateDashboardView;
window.activateQadamDashboardViewFromHash = activateDashboardViewFromHash;
window.resolveQadamDashboardHash = resolveDashboardHash;
window.setQadamDashboardDebugMode = setDashboardDebugMode;
window.qadamDashboardDebugModeEnabled = dashboardDebugModeEnabled;
window.canonicalQadamDashboardStatus = canonicalStatusRecord;
window.canonicalQadamDashboardStatusLabel = canonicalStatusLabel;
window.canonicalQadamDashboardStatusTone = canonicalStatusTone;
window.buildQadamDashboardViewModels = buildQadamDashboardViewModels;
window.buildQadamBalanceTickerModel = buildBalanceTickerModel;
window.buildQadamTradeTimelineTokens = buildTradeTimelineTokens;
window.buildQadamDashboardSafetyStripModel = buildDashboardSafetyStripModel;
window.buildQadamDashboardOverviewModel = buildOverviewModel;
window.buildQadamDashboardTradesModel = buildTradesModel;
window.buildQadamDashboardSourcesModel = buildSourcesModel;
window.buildQadamDashboardReasoningModel = buildReasoningModel;
window.buildQadamDashboardPerformanceModel = buildPerformanceModel;
window.buildQadamDashboardSystemConnectivityModel = buildSystemConnectivityModel;
window.buildQadamDashboardOperationsModel = buildOperationsModel;
window.buildQadamDashboardGovernanceModel = buildGovernanceModel;
window.renderQadamDashboardStatus = renderQadamDashboardStatus;
