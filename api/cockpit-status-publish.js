const crypto = require("node:crypto");
const zlib = require("node:zlib");

const MAX_COMPRESSED_BYTES = 4 * 1024 * 1024;
const MAX_UNCOMPRESSED_BYTES = 16 * 1024 * 1024;
const STATUS_BUCKET = process.env.QADAM_STATUS_STORAGE_BUCKET || "qadam-public-status-private";
const STATUS_OBJECT = process.env.QADAM_STATUS_STORAGE_OBJECT || "latest.json";

function safeEqual(left, right) {
    const a = Buffer.from(String(left || ""));
    const b = Buffer.from(String(right || ""));
    return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function jsonResponse(res, status, payload) {
    res.setHeader("content-type", "application/json; charset=utf-8");
    res.setHeader("cache-control", "no-store, max-age=0");
    res.status(status).send(JSON.stringify(payload));
}

async function readBody(req) {
    const chunks = [];
    let size = 0;
    for await (const chunk of req) {
        size += chunk.length;
        if (size > MAX_COMPRESSED_BYTES) throw new Error("compressed_payload_too_large");
        chunks.push(chunk);
    }
    const compressed = Buffer.concat(chunks);
    const raw = req.headers["content-encoding"] === "gzip"
        ? zlib.gunzipSync(compressed, { maxOutputLength: MAX_UNCOMPRESSED_BYTES })
        : compressed;
    if (raw.length > MAX_UNCOMPRESSED_BYTES) throw new Error("payload_too_large");
    return raw;
}

function validateBoundary(payload) {
    if (!payload || payload.mode !== "paper") return "paper_mode_required";
    if (payload.d1_snapshot?.public_safe !== true) return "public_safe_snapshot_required";
    if (payload.d1_snapshot?.read_only !== true) return "read_only_snapshot_required";
    if (payload.capital?.live_capital_enabled !== false) return "live_capital_must_be_disabled";
    if (payload.live_bridge?.broker_write_route !== false) return "broker_write_route_forbidden";
    if (payload.live_bridge?.local_orchestrator_exposed !== false) return "local_orchestrator_exposure_forbidden";
    return null;
}

async function ensurePrivateBucket(supabaseUrl, supabaseKey) {
    const base = supabaseUrl.replace(/\/$/, "");
    const headers = {
        apikey: supabaseKey,
        authorization: `Bearer ${supabaseKey}`,
        "content-type": "application/json"
    };
    const existing = await fetch(`${base}/storage/v1/bucket/${encodeURIComponent(STATUS_BUCKET)}`, {
        headers,
        cache: "no-store"
    });
    if (existing.ok) return;
    if (existing.status !== 404) throw new Error(`status_bucket_check_${existing.status}`);
    const created = await fetch(`${base}/storage/v1/bucket`, {
        method: "POST",
        headers,
        body: JSON.stringify({
            id: STATUS_BUCKET,
            name: STATUS_BUCKET,
            public: false,
            file_size_limit: MAX_UNCOMPRESSED_BYTES,
            allowed_mime_types: ["application/json"]
        })
    });
    if (!created.ok && created.status !== 409) {
        throw new Error(`status_bucket_create_${created.status}`);
    }
}

async function storeSignedSnapshot(supabaseUrl, supabaseKey, record) {
    await ensurePrivateBucket(supabaseUrl, supabaseKey);
    const objectPath = STATUS_OBJECT.split("/").map(encodeURIComponent).join("/");
    const endpoint = `${supabaseUrl.replace(/\/$/, "")}/storage/v1/object/${encodeURIComponent(STATUS_BUCKET)}/${objectPath}`;
    const response = await fetch(endpoint, {
        method: "POST",
        headers: {
            apikey: supabaseKey,
            authorization: `Bearer ${supabaseKey}`,
            "content-type": "application/json",
            "cache-control": "no-store",
            "x-upsert": "true"
        },
        body: JSON.stringify(record)
    });
    if (!response.ok) throw new Error(`status_object_store_${response.status}`);
}

module.exports = async function cockpitStatusPublish(req, res) {
    if (req.method !== "POST") {
        res.setHeader("allow", "POST");
        return jsonResponse(res, 405, { status: "method_not_allowed" });
    }
    const publishToken = process.env.QADAM_STATUS_PUBLISH_TOKEN || "";
    const signingKey = process.env.QADAM_STATUS_BRIDGE_SIGNING_KEY || "";
    const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || "";
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SECRET_KEY || "";
    if (!publishToken || !signingKey || !supabaseUrl || !supabaseKey) {
        return jsonResponse(res, 503, { status: "receiver_not_configured" });
    }
    const bearer = String(req.headers.authorization || "").replace(/^Bearer\s+/i, "");
    if (!safeEqual(bearer, publishToken)) {
        return jsonResponse(res, 401, { status: "unauthorized" });
    }

    try {
        const raw = await readBody(req);
        const digest = crypto.createHash("sha256").update(raw).digest("hex");
        const expectedSignature = crypto.createHmac("sha256", signingKey).update(raw).digest("hex");
        if (!safeEqual(req.headers["x-qadam-payload-digest"], digest)) {
            return jsonResponse(res, 400, { status: "payload_digest_mismatch" });
        }
        if (!safeEqual(req.headers["x-qadam-signature"], expectedSignature)) {
            return jsonResponse(res, 401, { status: "signature_invalid" });
        }
        const canonicalPayload = raw.toString("utf8");
        const payload = JSON.parse(canonicalPayload);
        const boundaryError = validateBoundary(payload);
        if (boundaryError) return jsonResponse(res, 400, { status: boundaryError });

        const storedAt = new Date().toISOString();
        const canonicalPayloadGzipBase64 = zlib
            .gzipSync(raw, { level: 6 })
            .toString("base64");
        await storeSignedSnapshot(supabaseUrl, supabaseKey, {
            generated_at: payload.generated_at,
            payload_digest: digest,
            signature: expectedSignature,
            canonical_payload_encoding: "gzip_base64",
            canonical_payload_gzip_base64: canonicalPayloadGzipBase64,
            stored_at: storedAt
        });
        return jsonResponse(res, 201, {
            status: "stored",
            payload_digest: digest,
            stored_at: storedAt,
            storage_backend: "supabase_private_object",
            boundary: "Public-safe status only. No command or trading authority."
        });
    } catch (error) {
        return jsonResponse(res, 400, {
            status: "invalid_public_status_payload",
            error: error && error.message ? error.message : "invalid payload"
        });
    }
};

module.exports.config = { api: { bodyParser: false } };
