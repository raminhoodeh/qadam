#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const repoRoot = path.resolve(__dirname, "..");
const rendererPath = path.join(repoRoot, "landing-page-repo", "dashboard.js");
const statusPath = path.join(repoRoot, "landing-page-repo", "status", "cockpit-status.json");

const rendererCode = fs.readFileSync(rendererPath, "utf8");
const status = JSON.parse(fs.readFileSync(statusPath, "utf8"));

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function loadRenderer() {
    const document = {
        documentElement: { dataset: {} },
        querySelector() {
            return null;
        },
        querySelectorAll() {
            return [];
        }
    };
    const window = { document };
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
        window
    };
    window.window = window;
    vm.createContext(context);
    vm.runInContext(rendererCode, context, { filename: rendererPath });
    return context;
}

const context = loadRenderer();
assert(typeof context.buildQadamDashboardViewModels === "function", "dashboard view-model builder not exported");
assert(typeof context.renderContractPortfolioBlock === "function", "contract portfolio renderer not available");

const capitalCurve = Array.isArray(status.capital?.equity_curve) ? status.capital.equity_curve : [];
assert(capitalCurve.length >= 20, `expected at least 20 real capital.equity_curve points, got ${capitalCurve.length}`);

const models = context.buildQadamDashboardViewModels(status, { key: "live_bridge" });
const portfolio = models.founder_contract_model?.portfolio || {};
assert(portfolio.timeline_source === "capital.equity_curve", `portfolio timeline source should be capital.equity_curve, got ${portfolio.timeline_source}`);
assert(portfolio.equity_curve.length === capitalCurve.length, "founder portfolio must mirror the real capital.equity_curve length");
assert(portfolio.mirror_freshness_status === status.capital.mirror_freshness_status, "mirror_freshness_status must come from capital.mirror_freshness_status");
assert(portfolio.closed_trade_count === status.capital.maturity_closed_trade_count, "closed trade count must come from maturity_closed_trade_count");
assert(portfolio.maturity_closed_trade_target === status.capital.maturity_closed_trade_target, "closed trade target must come from maturity_closed_trade_target");

const first = portfolio.equity_curve[0];
const last = portfolio.equity_curve.at(-1);
assert(first.equity_gbp === capitalCurve[0].equity_gbp, "first equity point must match capital.equity_curve");
assert(last.equity_gbp === capitalCurve.at(-1).equity_gbp, "last equity point must match capital.equity_curve");

const html = context.renderContractPortfolioBlock(portfolio);
[
    "data-cc6-real-portfolio-timeline=\"capital.equity_curve\"",
    "data-paper-capacity-line",
    "20 live points",
    "stale mirror",
    "Closed/target",
    "7/100",
    "capital.equity_curve",
    "Balance",
    "Delta",
    "Drawdown",
    "Realized",
    "Unrealized"
].forEach((needle) => {
    assert(html.includes(needle), `portfolio timeline render missing ${needle}`);
});

assert(
    !context.renderContractPortfolioBlock.toString().includes("paperAccountEquityPoints"),
    "CC6 founder portfolio renderer must not fabricate fallback equity points"
);

const missing = clone(status);
missing.capital = { ...missing.capital, equity_curve: [] };
missing.mission_control = {
    ...missing.mission_control,
    portfolio: {
        ...missing.mission_control.portfolio,
        equity_curve: []
    }
};
const missingModels = context.buildQadamDashboardViewModels(missing, { key: "live_bridge" });
const missingPortfolio = missingModels.founder_contract_model.portfolio;
const missingHtml = context.renderContractPortfolioBlock(missingPortfolio);
assert(missingPortfolio.timeline_source === "missing", "empty exported curves must stay missing");
assert(missingPortfolio.equity_curve.length === 0, "empty exported curves must not gain fallback points");
assert(missingHtml.includes("data-cc6-real-portfolio-timeline=\"missing\""), "empty state must identify missing real timeline");
assert(!missingHtml.includes("data-paper-capacity-line"), "missing real timeline must not render a chart line");

console.log("dashboard_cc6_real_portfolio_timeline=ok");
console.log(`dashboard_cc6_points=${portfolio.equity_curve.length}`);
console.log(`dashboard_cc6_mirror=${portfolio.mirror_freshness_status}`);
