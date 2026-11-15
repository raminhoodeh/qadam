const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const Module = require('node:module');

test('signed three-day snapshot is explicitly historical; overdue and future snapshots are not current', async () => {
    const apiPath = path.resolve(__dirname, '../api/cockpit-status.js');
    const oldLoad = Module._load;
    const previous = { ...process.env };
    let generated;
    process.env.BLOB_READ_WRITE_TOKEN = 'fixture';
    process.env.QADAM_STATUS_BRIDGE_SIGNING_KEY = 'fixture';
    delete process.env.QADAM_STATUS_BRIDGE_STALE_AFTER_SECONDS;
    Module._load = function (name, ...args) {
        if (name === '../lib/status-storage') return {
            blobConfigured: () => true,
            readBlobSnapshot: async () => {
                const canonical = JSON.stringify({ generated_at: generated, mode: 'paper' });
                return { canonical_payload: canonical,
                    payload_digest: crypto.createHash('sha256').update(canonical).digest('hex'),
                    signature: crypto.createHmac('sha256', 'fixture').update(canonical).digest('hex') };
            }
        };
        return oldLoad.call(this, name, ...args);
    };
    try {
        delete require.cache[apiPath];
        const handler = require(apiPath);
        for (const [age, state] of [[3 * 86400, 'scheduled_snapshot'], [5 * 86400, 'stale'], [-60, 'stale']]) {
            generated = new Date(Date.now() - age * 1000).toISOString();
            let payload;
            const response = { setHeader() {}, status(code) { assert.equal(code, 200); return this; },
                send(value) { payload = JSON.parse(String(value)); } };
            await handler({ method: 'GET', headers: {} }, response);
            assert.equal(payload.live_bridge.delivery.state, state);
            assert.equal(payload.live_bridge.delivery.as_of, generated);
            assert.equal(payload.live_bridge.delivery.current_updates_channel, 'Telegram');
        }
    } finally { Module._load = oldLoad; process.env = previous; delete require.cache[apiPath]; }
});

test('browser polling and fallback expiry match the four-day delivery contract', () => {
    const source = fs.readFileSync(path.resolve(__dirname, '../dashboard.js'), 'utf8');
    assert.match(source, /DASHBOARD_STATUS_REFRESH_MS = 4 \* 24 \* 60 \* 60 \* 1000/);
    assert.match(source, /latest trades and alerts on Telegram/);
    assert.doesNotMatch(source, /DASHBOARD_STATUS_REFRESH_MS = 15000/);
});
