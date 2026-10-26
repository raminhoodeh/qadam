"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const document = { documentElement: { dataset: {} }, querySelector() { return null; }, querySelectorAll() { return []; } };
const window = { document };
const context = vm.createContext({ document, window, console, Intl,
    localStorage: { getItem() { return null; }, setItem() {} },
    fetch: async () => { throw new Error("network_not_permitted"); } });
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "dashboard.js"), "utf8"), context);
const capital = { account_currency: "USD", display_currency: "USD" };

test("quantity fills use actual fill quantity and price, never a missing notional zero", () => {
    const order = { instrument: "XLE", status: "filled", direction: "buy", order_type: "market",
        quantity: 2, filled_quantity: 2, filled_avg_price: 69.14, notional_gbp: null,
        filled_at: "2026-10-26T13:34:00Z" };
    const row = context.buildTradeTimelineTokens({ capital: { ...capital, orders: [order] } })[0];
    assert.equal(row.detail, `buy market · ${context.formatCapitalMoney(138.28, capital)} filled`);
    assert.doesNotMatch(row.detail, /US\$0/);
    assert.equal(context.tradeTimelineOrderValue({ ...order, quantity: 4, filled_quantity: 1 }, capital),
        `${context.formatCapitalMoney(69.14, capital)} filled`);
});

test("unfilled orders report explicit notional or unknown value, not an invented fill", () => {
    assert.match(context.tradeTimelineOrderValue({ notional_gbp: 200 }, capital), /200/);
    for (const value of [null, undefined, "", 0, NaN, Infinity, -1]) {
        const label = context.tradeTimelineOrderValue({ quantity: 2, notional_gbp: value }, capital);
        assert.equal(label, "2 units · value unavailable");
        assert.equal(context.tradeTimelineOrderValue({ filled_quantity: 2, filled_avg_price: value }, capital), "value unavailable");
    }
    assert.equal(context.tradeTimelineOrderValue({ filled_quantity: 1e300, filled_avg_price: 1e300 }, capital), "value unavailable");
});

test("submitted projections do not substitute risk budgets for executed value", () => {
    const row = context.buildTradeTimelineTokens({ capital,
        trade_layer: { submitted_orders: [{ instrument: "USO", quantity: 1, risk_size_gbp: 500 }] } })[0];
    assert.match(row.detail, /1 units · value unavailable/);
    assert.doesNotMatch(row.detail, /500/);
});
