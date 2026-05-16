const SUPABASE_URL = "https://eipijgublkypksygsyet.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_PWIXQ4VlNZb1O5bu-2aeXA_-3lNMq-y";
const ALLOWLIST = ["raminhoodeh@gmail.com", "troycookecareer@gmail.com", "isioras@yahoo.co.uk"];

const qadamAuth = window.supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);

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

async function wireLogin() {
    const form = document.querySelector("[data-login-form]");
    if (!form) return;

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

    const { data } = await qadamAuth.auth.getSession();
    const session = data.session;
    if (!session) {
        window.location.replace(`/login/?next=${encodeURIComponent("/dashboard/")}`);
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

    dashboard.classList.remove("hidden");
}

async function wireSignOut() {
    const button = document.querySelector("[data-signout]");
    if (!button) return;
    button.addEventListener("click", async () => {
        await qadamAuth.auth.signOut();
        window.location.assign("/login/");
    });
}

wireLogin();
wireSignUp();
wireDashboard();
wireSignOut();
