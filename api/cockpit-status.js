const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const zlib = require("node:zlib");

const STATUS_BUCKET = process.env.QADAM_STATUS_STORAGE_BUCKET || "qadam-public-status-private";
const STATUS_OBJECT = process.env.QADAM_STATUS_STORAGE_OBJECT || "latest.json";
const DEFAULT_STATUS_STALE_AFTER_SECONDS = 600;
const MAX_UNCOMPRESSED_BYTES = 16 * 1024 * 1024;

function statusStaleAfterSeconds() {
    const configured = Number(
        process.env.QADAM_STATUS_BRIDGE_STALE_AFTER_SECONDS
        || DEFAULT_STATUS_STALE_AFTER_SECONDS
    );
    return Number.isFinite(configured) && configured > 0
        ? configured
        : DEFAULT_STATUS_STALE_AFTER_SECONDS;
}

function stableStringify(value) {
    if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
    if (value && typeof value === "object") {
        return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
    }
    return JSON.stringify(value);
}

function safeEqual(left, right) {
    const a = Buffer.from(String(left || ""));
    const b = Buffer.from(String(right || ""));
    return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function decorate(payload, delivery) {
    return {
        ...payload,
        live_bridge: {
            ...(payload.live_bridge || {}),
            delivery
        }
    };
}

function snapshotAgeSeconds(payload) {
    const generatedMs = Date.parse(
        payload.generated_at
        || payload.dashboard_portfolio?.generated_at
        || payload.capital?.observed_at
        || ""
    );
    return Number.isFinite(generatedMs)
        ? Math.max(0, Math.floor((Date.now() - generatedMs) / 1000))
        : null;
}

function sendStatus(req, res, payload, digest, source) {
    const etag = `"${digest}"`;
    res.setHeader("content-type", "application/json; charset=utf-8");
    res.setHeader("cache-control", "private, no-cache, must-revalidate");
    res.setHeader("etag", etag);
    res.setHeader("x-qadam-status-source", source);
    if (req.headers["if-none-match"] === etag) return res.status(304).end();
    if (req.method === "HEAD") return res.status(200).end();
    const serialized = Buffer.from(JSON.stringify(payload), "utf8");
    if (String(req.headers["accept-encoding"] || "").includes("gzip")) {
        res.setHeader("content-encoding", "gzip");
        res.setHeader("vary", "accept-encoding");
        return res.status(200).send(zlib.gzipSync(serialized, { level: 6 }));
    }
    return res.status(200).send(serialized);
}

function canonicalPayloadFromRecord(record) {
    if (record.canonical_payload) return record.canonical_payload;
    if (
        record.canonical_payload_encoding === "gzip_base64"
        && record.canonical_payload_gzip_base64
    ) {
        return zlib.gunzipSync(
            Buffer.from(record.canonical_payload_gzip_base64, "base64"),
            { maxOutputLength: MAX_UNCOMPRESSED_BYTES }
        ).toString("utf8");
    }
    return "";
}

async function latestPublishedSnapshot() {
    const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || "";
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SECRET_KEY || "";
    const signingKey = process.env.QADAM_STATUS_BRIDGE_SIGNING_KEY || "";
    if (!supabaseUrl || !supabaseKey || !signingKey) return null;
    const objectPath = STATUS_OBJECT.split("/").map(encodeURIComponent).join("/");
    const endpoint = `${supabaseUrl.replace(/\/$/, "")}/storage/v1/object/authenticated/${encodeURIComponent(STATUS_BUCKET)}/${objectPath}`;
    const response = await fetch(endpoint, {
        headers: {
            apikey: supabaseKey,
            authorization: `Bearer ${supabaseKey}`,
            "cache-control": "no-cache"
        },
        cache: "no-store"
    });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`status_store_${response.status}`);
    const record = await response.json();
    const canonical = canonicalPayloadFromRecord(record);
    if (!canonical) throw new Error("stored_status_canonical_payload_missing");
    const digest = crypto.createHash("sha256").update(canonical).digest("hex");
    const signature = crypto.createHmac("sha256", signingKey).update(canonical).digest("hex");
    if (!safeEqual(record.payload_digest, digest) || !safeEqual(record.signature, signature)) {
        throw new Error("stored_status_signature_invalid");
    }
    const verifiedPayload = JSON.parse(canonical);
    const generatedMs = Date.parse(verifiedPayload.generated_at || record.generated_at || "");
    const ageSeconds = Number.isFinite(generatedMs) ? Math.max(0, Math.floor((Date.now() - generatedMs) / 1000)) : null;
    const staleAfter = statusStaleAfterSeconds();
    return {
        payload: decorate(verifiedPayload, {
            state: ageSeconds !== null && ageSeconds <= staleAfter ? "live" : "stale",
            source: "signed_private_status_object",
            storage_backend: "supabase_private_object",
            stored_at: record.stored_at,
            age_seconds: ageSeconds,
            stale_after_seconds: staleAfter,
            signature_verified: true,
            read_only: true
        }),
        digest
    };
}

module.exports = async function cockpitStatus(req, res) {
    if (!["GET", "HEAD"].includes(req.method)) {
        res.setHeader("allow", "GET, HEAD");
        return res.status(405).send(JSON.stringify({ status: "method_not_allowed" }));
    }
    const statusPath = path.join(process.cwd(), "status", "cockpit-status.json");
    try {
        const published = await latestPublishedSnapshot();
        if (published) return sendStatus(req, res, published.payload, published.digest, "signed_public_status_store");
    } catch (error) {
        res.setHeader("x-qadam-live-bridge-error", "signed_snapshot_unavailable");
    }
    try {
        const raw = fs.readFileSync(statusPath, "utf8");
        const payload = JSON.parse(raw);
        const digest = crypto.createHash("sha256").update(stableStringify(payload)).digest("hex");
        const ageSeconds = snapshotAgeSeconds(payload);
        const staleAfter = statusStaleAfterSeconds();
        const delivery = {
            state: "static_fallback",
            source: "deployed_static_snapshot",
            age_seconds: ageSeconds,
            stale_after_seconds: staleAfter,
            signature_verified: false,
            read_only: true
        };
        if (ageSeconds === null || ageSeconds > staleAfter) {
            delivery.state = "stale_static_fallback";
        }
        return sendStatus(req, res, decorate(payload, delivery), digest, "deployed_static_snapshot");
    } catch (error) {
        res.setHeader("content-type", "application/json; charset=utf-8");
        return res.status(503).send(JSON.stringify({
            status: "cockpit_status_unavailable",
            error: error && error.message ? error.message : "status file unavailable",
            boundary: "Read-only public status bridge. No command, broker, or live-capital authority."
        }));
    }
};
