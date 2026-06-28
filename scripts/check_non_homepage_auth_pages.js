#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");

function read(relativePath) {
    return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function assertIncludes(text, needles, label) {
    needles.forEach((needle) => {
        assert(text.includes(needle), `${label} missing ${needle}`);
    });
}

const login = read("landing-page-repo/login/index.html");
const signup = read("landing-page-repo/sign-up/index.html");
const css = read("landing-page-repo/auth.css");
const authJs = read("landing-page-repo/auth.js");

assertIncludes(login, [
    '<body class="qadam-auth-page">',
    'data-auth-page="login"',
    'qadam-auth-shell',
    'qadam-auth-header',
    'qadam-auth-hero',
    'qadam-auth-intro',
    'qadam-auth-proof-list',
    'qadam-auth-panel',
    'data-login-form',
    'name="email"',
    'name="password"',
    'autocomplete="email"',
    'autocomplete="current-password"',
    'data-status aria-live="polite"',
    '<script src="/auth.js"></script>'
], "login page");

assertIncludes(signup, [
    '<body class="qadam-auth-page">',
    'data-auth-page="sign-up"',
    'qadam-auth-shell',
    'qadam-auth-header',
    'qadam-auth-hero',
    'qadam-auth-intro',
    'qadam-auth-proof-list',
    'qadam-auth-panel',
    'data-signup-form',
    'name="email"',
    'name="password"',
    'autocomplete="email"',
    'autocomplete="new-password"',
    'required minlength="8"',
    'data-status aria-live="polite"',
    '<script src="/auth.js"></script>'
], "sign-up page");

assertIncludes(css, [
    "body.qadam-auth-page",
    ".qadam-auth-page .qadam-auth-shell",
    ".qadam-auth-page .qadam-auth-header",
    ".qadam-auth-page .qadam-auth-nav-link",
    ".qadam-auth-page .qadam-auth-hero",
    ".qadam-auth-proof-list",
    ".qadam-auth-page .qadam-auth-panel",
    ".qadam-auth-page .qadam-auth-submit",
    ".qadam-auth-page .status.error",
    "@media (max-width: 760px)"
], "auth css");

assertIncludes(authJs, [
    'document.querySelector("[data-login-form]")',
    'document.querySelector("[data-signup-form]")',
    'document.querySelector("[data-status]")',
    'qadamAuth.auth.signInWithPassword',
    'qadamAuth.auth.signUp'
], "auth js");

[
    /PVZ[0-9A-Za-z_-]{20,}/,
    /\d{6,}:[A-Za-z0-9_-]{20,}/,
    /OPENAI_API_KEY=/,
    /ANTHROPIC_API_KEY=/,
    /TELEGRAM_BOT_TOKEN=/
].forEach((pattern) => {
    assert(!pattern.test(login), `login page contains unsafe public text: ${pattern}`);
    assert(!pattern.test(signup), `sign-up page contains unsafe public text: ${pattern}`);
});

console.log("non_homepage_auth_pages=ok");
