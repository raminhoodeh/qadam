const SUPABASE_URL = "https://eipijgublkypksygsyet.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_PWIXQ4VlNZb1O5bu-2aeXA_-3lNMq-y";
const ALLOWLIST = ["raminhoodeh@gmail.com", "troycookecareer@gmail.com", "akber.ali@hotmail.co.uk", "isioras@yahoo.co.uk", "danmerdad@hotmail.co.uk"];
const COMMENT_TABLE = "fund_manager_comments";
const COMMENT_TARGET_TYPES = new Set([
    "module",
    "source",
    "signal",
    "trade_candidate",
    "postmortem",
    "resource",
    "strategy",
    "system",
    "world_model"
]);
const COMMENT_STATUSES = new Set(["suggestion", "accepted", "rejected", "implemented"]);
const COMMENT_EXPORT_STATUSES = new Set(["accepted", "implemented"]);

// Restore only through a reviewed release after cloud auth and access checks pass.
const CLOUD_COLLABORATION_ENABLED = false;
const CLOUD_UNAVAILABLE_MESSAGE = "Cloud collaboration is temporarily unavailable. Login, account creation, the protected guide and comments are paused. The public dashboard remains read-only; follow Telegram for current updates.";
let qadamAuth = null;

async function initializeCloudCollaboration() {
    if (!CLOUD_COLLABORATION_ENABLED) return;
    if (typeof window.supabase?.createClient !== "function") {
        await new Promise((resolve) => {
            const script = document.createElement("script");
            const finish = () => {
                window.clearTimeout(timeout);
                script.onload = script.onerror = null;
                resolve();
            };
            const timeout = window.setTimeout(finish, 5000);
            script.src = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2";
            script.async = true;
            script.onload = script.onerror = finish;
            document.head.appendChild(script);
        });
    }
    if (typeof window.supabase?.createClient !== "function") return;
    try {
        qadamAuth = window.supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
    } catch (_error) {
        // Missing or unusable cloud auth must never unlock a protected surface.
    }
}

function showCloudUnavailable() {
    const status = document.querySelector("[data-cloud-status]");
    if (status) {
        status.textContent = CLOUD_UNAVAILABLE_MESSAGE;
        status.hidden = false;
    }
    showStatus(CLOUD_UNAVAILABLE_MESSAGE);
}

function disableCloudForm(form) {
    if (!form) return;
    form.querySelectorAll("input, select, textarea, button").forEach((control) => {
        control.disabled = true;
    });
    form.addEventListener("submit", (event) => event.preventDefault());
}

function disableForum() {
    disableCloudForm(document.querySelector("[data-comment-form]"));
    const summary = document.querySelector("[data-comments-summary]");
    if (summary) summary.textContent = "";
    const list = document.querySelector("[data-comments-list]");
    if (list) list.textContent = "Comments are temporarily unavailable. Follow Telegram for current updates.";
    document.querySelectorAll("[data-comment-status-action]").forEach((button) => {
        button.disabled = true;
    });
    showForumStatus("Comments are temporarily unavailable. Follow Telegram for current updates.", "error");
}

function cleanNext(value) {
    if (!value || !value.startsWith("/") || value.startsWith("//")) {
        return "/dashboard/";
    }
    return value;
}

function showStatus(message, type = "error") {
    const status = document.querySelector("[data-status]");
    if (!status) return;
    status.textContent = message;
    status.className = `status show ${type}`;
}

function emailIsAllowed(email) {
    return ALLOWLIST.includes(String(email || "").toLowerCase());
}

function forumStatusClass(status) {
    return String(status || "pending")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "") || "pending";
}

function showForumStatus(message, type = "ok") {
    const status = document.querySelector("[data-comments-status]");
    if (!status) return;
    status.textContent = message;
    status.className = `status show ${type}`;
}

function clearForumStatus() {
    const status = document.querySelector("[data-comments-status]");
    if (!status) return;
    status.textContent = "";
    status.className = "status";
}

function eventLogExportStatus(status) {
    return COMMENT_EXPORT_STATUSES.has(status) ? "pending_local_event_log_export" : "not_required";
}

function appendInlineBadge(parent, text, tone = "pending") {
    const badge = document.createElement("span");
    badge.className = `inline-badge ${forumStatusClass(tone)}`;
    badge.textContent = text;
    parent.appendChild(badge);
}

function commentValue(record, key, fallback = "") {
    return String(record?.[key] || fallback).replaceAll("_", " ");
}

function renderForumSummary(comments) {
    const summary = document.querySelector("[data-comments-summary]");
    if (!summary) return;
    const rows = [
        ["Forum comments", comments.length],
        ["Suggestions", comments.filter((comment) => ["suggestion", "open"].includes(comment.status)).length],
        ["Accepted", comments.filter((comment) => comment.status === "accepted").length],
        ["Implemented", comments.filter((comment) => comment.status === "implemented").length]
    ];
    summary.innerHTML = "";
    rows.forEach(([label, value]) => {
        const metric = document.createElement("div");
        metric.className = "metric";
        const span = document.createElement("span");
        span.textContent = label;
        const strong = document.createElement("strong");
        strong.textContent = value;
        metric.append(span, strong);
        summary.appendChild(metric);
    });
}

function renderForumComments(comments) {
    const list = document.querySelector("[data-comments-list]");
    if (!list) return;
    list.textContent = "";

    if (!comments.length) {
        const item = document.createElement("li");
        const strong = document.createElement("strong");
        strong.textContent = "No comments yet";
        const span = document.createElement("span");
        span.textContent = "Founding Fund Managers can add governance notes linked to dashboard objects.";
        item.append(strong, span);
        list.appendChild(item);
        return;
    }

    comments.forEach((comment) => {
        const item = document.createElement("li");
        const title = document.createElement("strong");
        title.textContent = `${commentValue(comment, "target_type", "module")} · ${commentValue(comment, "target_key", "general")}`;

        const body = document.createElement("span");
        body.textContent = commentValue(comment, "body", "No comment body.");

        const meta = document.createElement("div");
        meta.className = "comment-meta";
        appendInlineBadge(meta, commentValue(comment, "status", "suggestion"), comment.status || "suggestion");
        appendInlineBadge(meta, commentValue(comment, "visibility", "founding_fund_managers"), "online");
        appendInlineBadge(meta, commentValue(comment, "event_log_export_status", "not_required"), "pending");

        const small = document.createElement("small");
        const createdAt = comment.created_at ? new Date(comment.created_at).toLocaleString("en-GB") : "not timestamped";
        small.textContent = `${commentValue(comment, "author_email", "founding manager")} · ${createdAt}`;

        item.append(title, body, meta, small);

        if (comment.id) {
            const actions = document.createElement("div");
            actions.className = "comments-actions";
            ["accepted", "rejected", "implemented"].forEach((nextStatus) => {
                if (comment.status === nextStatus) return;
                const button = document.createElement("button");
                button.type = "button";
                button.dataset.commentStatusAction = nextStatus;
                button.dataset.commentId = comment.id;
                button.textContent = nextStatus;
                actions.appendChild(button);
            });
            item.appendChild(actions);
        }

        list.appendChild(item);
    });
}

function buildCommentPayload(form, session) {
    const formData = new FormData(form);
    const targetType = String(formData.get("target_type") || "").trim();
    const targetKey = String(formData.get("target_key") || "").trim();
    const status = String(formData.get("status") || "").trim();
    const body = String(formData.get("body") || "").trim();

    if (!COMMENT_TARGET_TYPES.has(targetType)) {
        throw new Error("Choose a valid reference type.");
    }
    if (!COMMENT_STATUSES.has(status)) {
        throw new Error("Choose a valid comment status.");
    }
    if (!targetKey) {
        throw new Error("Add the dashboard object this comment refers to.");
    }
    if (!body) {
        throw new Error("Add the comment body.");
    }

    return {
        author_id: session.user.id,
        author_email: String(session.user.email || "").toLowerCase(),
        target_type: targetType,
        target_key: targetKey,
        body,
        tags: [],
        status,
        visibility: "founding_fund_managers",
        event_log_export_status: eventLogExportStatus(status)
    };
}

async function loadForumComments() {
    if (!qadamAuth) throw new Error(CLOUD_UNAVAILABLE_MESSAGE);
    const { data, error } = await qadamAuth
        .from(COMMENT_TABLE)
        .select("id,created_at,updated_at,author_email,target_type,target_key,status,body,tags,visibility,event_log_export_status")
        .order("created_at", { ascending: false })
        .limit(20);

    if (error) throw error;
    const comments = Array.isArray(data) ? data : [];
    renderForumSummary(comments);
    renderForumComments(comments);
    clearForumStatus();
}

async function updateForumCommentStatus(commentId, status) {
    if (!qadamAuth) throw new Error(CLOUD_UNAVAILABLE_MESSAGE);
    if (!COMMENT_STATUSES.has(status)) {
        throw new Error("Invalid comment status.");
    }
    const { error } = await qadamAuth
        .from(COMMENT_TABLE)
        .update({
            status,
            event_log_export_status: eventLogExportStatus(status),
            updated_at: new Date().toISOString()
        })
        .eq("id", commentId);
    if (error) throw error;
}

async function wireFundManagerForum(session) {
    if (!qadamAuth) {
        disableForum();
        return;
    }
    if (!session || !emailIsAllowed(session.user.email)) return;
    const form = document.querySelector("[data-comment-form]");
    const list = document.querySelector("[data-comments-list]");
    if (!form || !list || form.dataset.forumWired === "true") return;
    form.dataset.forumWired = "true";

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = form.querySelector("button[type='submit']");
        button.disabled = true;
        try {
            const payload = buildCommentPayload(form, session);
            const { error } = await qadamAuth.from(COMMENT_TABLE).insert(payload);
            if (error) throw error;
            form.reset();
            showForumStatus("Comment added.", "ok");
            await loadForumComments();
        } catch (error) {
            showForumStatus(error.message || "Comment could not be saved.", "error");
        } finally {
            button.disabled = false;
        }
    });

    list.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-comment-status-action]");
        if (!button) return;
        button.disabled = true;
        try {
            await updateForumCommentStatus(button.dataset.commentId, button.dataset.commentStatusAction);
            showForumStatus("Comment status updated.", "ok");
            await loadForumComments();
        } catch (error) {
            showForumStatus(error.message || "Comment status could not be updated.", "error");
            button.disabled = false;
        }
    });

    try {
        showForumStatus("Loading Fund Manager forum...", "ok");
        await loadForumComments();
    } catch (error) {
        showForumStatus(error.message || "Comment table is not available yet.", "error");
    }
}

function showLoginQueryError() {
    const form = document.querySelector("[data-login-form]");
    if (!form) return;

    const params = new URLSearchParams(window.location.search);
    const error = params.get("error");
    if (error === "not-allowlisted") {
        showStatus("That account is not on the founding Fund Manager allowlist.");
    }
}

function dashboardIsPublicReadOnly() {
    return document.body?.classList.contains("qadam-dashboard-page")
        && document.querySelector("[data-dashboard]")?.dataset.publicReadOnly === "true";
}

async function wireLogin() {
    const form = document.querySelector("[data-login-form]");
    if (!form) return;
    if (!qadamAuth) {
        disableCloudForm(form);
        showCloudUnavailable();
        return;
    }

    const params = new URLSearchParams(window.location.search);
    const next = cleanNext(params.get("next"));

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = form.querySelector("button");
        button.disabled = true;

        const formData = new FormData(form);
        const email = String(formData.get("email") || "").trim().toLowerCase();
        const password = String(formData.get("password") || "");

        if (!email || !password) {
            showStatus("Enter both email and password.");
            button.disabled = false;
            return;
        }

        const { data, error } = await qadamAuth.auth.signInWithPassword({ email, password });
        if (error || !data.session) {
            showStatus(error?.message || "Supabase rejected those credentials.");
            button.disabled = false;
            return;
        }

        if (!emailIsAllowed(data.user.email)) {
            await qadamAuth.auth.signOut();
            showStatus("That email is signed in but not allowlisted for Qadam.");
            button.disabled = false;
            return;
        }

        window.location.assign(next);
    });
}

async function wireSignUp() {
    const form = document.querySelector("[data-signup-form]");
    if (!form) return;
    if (!qadamAuth) {
        disableCloudForm(form);
        showCloudUnavailable();
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = form.querySelector("button");
        button.disabled = true;

        const formData = new FormData(form);
        const email = String(formData.get("email") || "").trim().toLowerCase();
        const password = String(formData.get("password") || "");

        if (!email || !password) {
            showStatus("Enter both email and password.");
            button.disabled = false;
            return;
        }

        if (!emailIsAllowed(email)) {
            showStatus("That email is not on the founding Fund Manager allowlist.");
            button.disabled = false;
            return;
        }

        const { data, error } = await qadamAuth.auth.signUp({
            email,
            password,
            options: {
                emailRedirectTo: `${window.location.origin}/dashboard/`
            }
        });

        if (error) {
            showStatus(error.message);
            button.disabled = false;
            return;
        }

        if (data.session) {
            window.location.assign("/dashboard/");
            return;
        }

        showStatus("Account created. Check your email to confirm it, then log in.", "ok");
        button.disabled = false;
    });
}

async function wireDashboard() {
    const dashboard = document.querySelector("[data-dashboard]");
    if (!dashboard) return;

    const publicReadOnly = dashboardIsPublicReadOnly();
    if (!qadamAuth && !publicReadOnly) {
        showCloudUnavailable();
        return;
    }

    let session = null;
    if (qadamAuth) {
        try {
            const { data, error } = await qadamAuth.auth.getSession();
            if (error) throw error;
            session = data.session;
        } catch (_error) {
            document.body.dataset.cloudCollaboration = "unavailable";
            showCloudUnavailable();
            disableForum();
            if (!publicReadOnly) return;
        }
    }
    if (publicReadOnly) {
        const emailTarget = document.querySelector("[data-user-email]");
        if (emailTarget) {
            emailTarget.textContent = session?.user?.email || "public read-only visitor";
        }

        dashboard.hidden = false;
        dashboard.classList.remove("hidden");
        if (window.renderQadamDashboardStatus) {
            await window.renderQadamDashboardStatus(session || null);
        }
        if (session && emailIsAllowed(session.user.email)) {
            await wireFundManagerForum(session);
        } else if (!qadamAuth) {
            disableForum();
        }
        return;
    }

    if (!session) {
        const currentPath = cleanNext(`${window.location.pathname}${window.location.search}`);
        window.location.replace(`/login/?next=${encodeURIComponent(currentPath)}`);
        return;
    }

    if (!emailIsAllowed(session.user.email)) {
        await qadamAuth.auth.signOut();
        window.location.replace("/login/?error=not-allowlisted");
        return;
    }

    const emailTarget = document.querySelector("[data-user-email]");
    if (emailTarget) {
        emailTarget.textContent = session.user.email;
    }

    dashboard.hidden = false;
    dashboard.classList.remove("hidden");
    if (window.renderQadamDashboardStatus) {
        await window.renderQadamDashboardStatus(session);
    }
    await wireFundManagerForum(session);
}

async function wireSignOut() {
    const button = document.querySelector("[data-signout]");
    if (!button) return;
    if (!qadamAuth) {
        button.disabled = true;
        return;
    }
    button.addEventListener("click", async () => {
        await qadamAuth.auth.signOut();
        window.location.assign("/login/");
    });
}

async function initializeAuth() {
    await initializeCloudCollaboration();
    document.body.dataset.cloudCollaboration = qadamAuth ? "enabled" : "unavailable";
    if (!qadamAuth) showCloudUnavailable();
    showLoginQueryError();
    wireLogin();
    wireSignUp();
    wireSignOut();
    await wireDashboard();
}

initializeAuth();

function loadQuantumEdgeWaveFAssets() {
    if (!document.body?.classList.contains("qadam-dashboard-page")) return;
    if (!document.querySelector('link[data-qadam-wave-f-style]')) {
        const stylesheet = document.createElement("link");
        stylesheet.rel = "stylesheet";
        stylesheet.href = "/quantum-edge-wave-f.css?v=20261117-cloud-paused-v1";
        stylesheet.dataset.qadamWaveFStyle = "true";
        document.head.appendChild(stylesheet);
    }
    if (!document.querySelector('script[data-qadam-wave-f-script]')) {
        const script = document.createElement("script");
        script.src = "/quantum-edge-wave-f.js?v=20261117-cloud-paused-v1";
        script.async = true;
        script.dataset.qadamWaveFScript = "true";
        document.body.appendChild(script);
    }
}

function loadQuantumEdgePageAssets() {
    if (!document.body?.classList.contains("qadam-dashboard-page")) return;
    if (!document.querySelector('link[data-qadam-quantum-edge-page-style]')) {
        const stylesheet = document.createElement("link");
        stylesheet.rel = "stylesheet";
        stylesheet.href = "/quantum-edge-page.css?v=20261117-cloud-paused-v1";
        stylesheet.dataset.qadamQuantumEdgePageStyle = "true";
        document.head.appendChild(stylesheet);
    }
    if (!document.querySelector('script[data-qadam-quantum-edge-page-script]')) {
        const script = document.createElement("script");
        script.src = "/quantum-edge-page.js?v=20261117-cloud-paused-v1";
        script.async = true;
        script.dataset.qadamQuantumEdgePageScript = "true";
        document.body.appendChild(script);
    }
}

function loadQuantumDashboardRouteAssets(route) {
    if (!document.body?.classList.contains("qadam-dashboard-page")) return;
    route = route || {};
    const params = new URLSearchParams(window.location.search);
    const moduleId = route.moduleId || params.get("module") || "fund";
    const viewId = route.viewId || params.get("view") || "overview";
    if (
        (moduleId === "patterns" && viewId === "findings")
        || (moduleId === "decide" && viewId === "strategies")
    ) {
        loadQuantumEdgeWaveFAssets();
    }
    if (moduleId === "patterns" && viewId === "nonlinear") {
        loadQuantumEdgePageAssets();
    }
}

loadQuantumDashboardRouteAssets();
window.addEventListener("qadam-dashboard-route-change", (event) => {
    loadQuantumDashboardRouteAssets(event.detail || {});
});
