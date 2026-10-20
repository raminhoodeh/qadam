const OBJECT = "qadam-public-status/latest.json";
const MAX_RECORD_BYTES = 4 * 1024 * 1024;

function blobConfigured() {
    return Boolean(process.env.BLOB_READ_WRITE_TOKEN)
        && process.env.QADAM_STATUS_STORAGE_BACKEND !== "supabase";
}

async function writeBlobSnapshot(record, sdk) {
    const { put } = sdk || require("@vercel/blob");
    const body = JSON.stringify(record);
    if (Buffer.byteLength(body) > MAX_RECORD_BYTES) throw new Error("signed_record_too_large");
    await put(OBJECT, body, {
        access: process.env.QADAM_STATUS_BLOB_ACCESS || "private",
        token: process.env.BLOB_READ_WRITE_TOKEN,
        contentType: "application/json",
        addRandomSuffix: false,
        allowOverwrite: true,
        cacheControlMaxAge: 60,
        abortSignal: AbortSignal.timeout(10000)
    });
}

async function readBlobSnapshot(sdk) {
    const { get } = sdk || require("@vercel/blob");
    const result = await get(OBJECT, {
        access: process.env.QADAM_STATUS_BLOB_ACCESS || "private",
        token: process.env.BLOB_READ_WRITE_TOKEN,
        useCache: false,
        abortSignal: AbortSignal.timeout(10000)
    });
    if (!result || result.statusCode !== 200 || !result.stream) return null;
    const reader = result.stream.getReader();
    const chunks = [];
    let size = 0;
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            size += value.byteLength;
            if (size > MAX_RECORD_BYTES) throw new Error("signed_record_too_large");
            chunks.push(Buffer.from(value));
        }
    } finally {
        await reader.cancel();
    }
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

module.exports = { blobConfigured, writeBlobSnapshot, readBlobSnapshot };
