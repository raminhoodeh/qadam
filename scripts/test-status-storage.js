const { test } = require("node:test");
const assert = require("node:assert/strict");
const { writeBlobSnapshot, readBlobSnapshot } = require("../lib/status-storage");

test("signed snapshot storage overwrites one bounded object, not history", async () => {
    const record = { payload_digest: "digest", signature: "hmac", canonical_payload: "{}" };
    const calls = [];
    await writeBlobSnapshot(record, { put: async (...args) => calls.push(args) });
    assert.equal(calls[0][0], "qadam-public-status/latest.json");
    assert.equal(calls[0][2].allowOverwrite, true);
    assert.equal(calls[0][2].addRandomSuffix, false);
    assert.equal(calls[0][2].access, "private");
    const read = await readBlobSnapshot({ get: async (_, options) => {
        assert.equal(options.useCache, false);
        return { statusCode: 200, stream: new Response(JSON.stringify(record)).body };
    }});
    assert.deepEqual(read, record);
});

test("missing snapshot is absent; oversized records never write", async () => {
    assert.equal(await readBlobSnapshot({ get: async () => null }), null);
    await assert.rejects(() => writeBlobSnapshot({ huge: "x".repeat(5*1024*1024) }, {
        put: async () => assert.fail("must not write")
    }), /too_large/);
});
